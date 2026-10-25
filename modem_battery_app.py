#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modem Monitor, Menu Bar Widget & SMS/Call Center for macOS
- Battery percentage & status in macOS Menu Bar with <= 10% alerts
- Real-time SMS & Missed Call desktop notifications
- Built-in Local Web Dashboard for reading/sending SMS, USSD, and modem controls
"""

import sys
import os
import time
import threading
import subprocess
import webbrowser
import rumps

from modem_client import ModemClient
import web_dashboard

CHECK_INTERVAL_SECONDS = 30
DASHBOARD_URL = "http://127.0.0.1:8080"
MODEM_PANEL_URL = "http://192.168.1.1"

# Persian digits translation table
PERSIAN_DIGITS_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(val) -> str:
    """Converts standard digits to clean Persian digits."""
    if val is None or val == "--" or str(val).strip() == "":
        return "--"
    return str(val).translate(PERSIAN_DIGITS_MAP)


def format_gauge(percent: int, length: int = 8) -> str:
    """Creates a visual ASCII gauge bar like [███░░░░░]."""
    clamped = max(0, min(100, int(percent)))
    filled = int(round(length * (clamped / 100.0)))
    return "█" * filled + "░" * (length - filled)


def format_signal(sig_val) -> str:
    """Formats signal quality with visual signal bars and descriptive Persian label."""
    try:
        s = int(sig_val)
    except (ValueError, TypeError):
        return "--"

    bars_map = ["░░░░", " ▂░░", " ▂▄░", " ▂▄▆", " ▂▄▆█", " ▂▄▆█"]
    bars = bars_map[min(max(0, s), 5)]
    labels = {
        0: "بدون سیگنال",
        1: "بسیار ضعیف",
        2: "ضعیف",
        3: "متوسط",
        4: "خوب",
        5: "عالی",
    }
    label = labels.get(s, "نامشخص")
    return f"{fa_num(s)} از ۵ ({label}) {bars}"


def format_speed_fa(bps_val) -> str:
    """Converts bytes per second to readable Persian speed string."""
    try:
        b = float(bps_val)
        if b < 1024:
            return f"{fa_num(int(b))} بایت/ث"
        elif b < 1024 * 1024:
            kb = round(b / 1024.0, 1)
            kb_str = str(int(kb)) if kb.is_integer() else f"{kb:.1f}"
            return f"{fa_num(kb_str)} کیلوبایت/ث"
        else:
            mb = round(b / (1024.0 * 1024.0), 2)
            return f"{fa_num(f'{mb:.2f}')} مگابایت/ث"
    except Exception:
        return f"{fa_num(0)} بایت/ث"


def format_uptime_fa(seconds_val) -> str:
    """Converts runtime seconds to readable Persian hours and minutes."""
    try:
        sec = int(seconds_val)
        hours = sec // 3600
        mins = (sec % 3600) // 60
        if hours > 0:
            return f"{fa_num(hours)} ساعت و {fa_num(mins)} دقیقه"
        return f"{fa_num(mins)} دقیقه"
    except Exception:
        return "--"


def format_traffic_fa(bytes_val) -> str:
    """Converts bytes to gigabytes in Persian."""
    try:
        b = float(bytes_val)
        gb = b / (1024.0 ** 3)
        return f"{fa_num(f'{gb:.1f}')} گیگابایت"
    except Exception:
        return "--"


def send_macos_notification(title: str, message: str, sound: str = "Ping"):
    safe_title = title.replace('"', '\\"')
    safe_msg = message.replace('"', '\\"')
    script = f'display notification "{safe_msg}" with title "{safe_title}" sound name "{sound}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False, timeout=2)
    except Exception as e:
        print(f"Error sending notification: {e}", file=sys.stderr)


class ModemBatteryApp(rumps.App):
    def __init__(self):
        super(ModemBatteryApp, self).__init__("مودم", title="🔋 ...")

        self.client = ModemClient()

        # State tracking
        self.alerted_10 = False
        self.alerted_5 = False
        self.is_connected = False

        # SMS & Missed Call tracking
        self.seen_sms_ids = set()
        self.first_sms_check = True
        self.last_missed_call = None

        # Build Menu Items
        # 1. Header & Status
        self.item_header = rumps.MenuItem("مودم همراه ایرانسل (NWR-945X)", callback=None)
        self.item_status = rumps.MenuItem("  وضعیت ارتباط: در حال اتصال...", callback=None)

        # 2. Battery & Power
        self.item_battery = rumps.MenuItem("  باتری: در حال بررسی...", callback=None)

        # 3. Signal & Network
        self.item_signal = rumps.MenuItem("  کیفیت آنتن: --", callback=None)
        self.item_speed = rumps.MenuItem("  سرعت تبادل داده: --", callback=None)
        self.item_clients = rumps.MenuItem("  دستگاه‌های متصل: --", callback=None)

        # 4. Communications (SMS & Calls)
        self.item_sms = rumps.MenuItem("  صندوق پیامک‌ها: --", callback=None)
        self.item_missed_call = rumps.MenuItem("  آخرین تماس بی‌پاسخ: بدون تماس", callback=None)

        # 5. Telemetry & Data Usage
        self.item_uptime = rumps.MenuItem("  مدت روشن بودن: --", callback=None)
        self.item_traffic = rumps.MenuItem("  حجم تبادل کل: --", callback=None)

        # 6. Action Items
        self.item_open_dashboard = rumps.MenuItem("💬 صندوق پیامک‌ها و دشبورد هوشمند (وب)", callback=self.open_dashboard)
        self.item_open_modem = rumps.MenuItem("🌐 ورود به پنل تنظیمات مودم (192.168.1.1)", callback=self.open_modem_panel)
        self.item_refresh = rumps.MenuItem("🔄 بروزرسانی وضعیت", callback=self.manual_refresh)
        self.item_quit = rumps.MenuItem("❌ خروج از برنامه", callback=self.quit_app)

        # Menu Layout
        self.menu = [
            self.item_header,
            self.item_status,
            None,  # Separator
            self.item_battery,
            self.item_signal,
            self.item_speed,
            self.item_clients,
            None,  # Separator
            self.item_sms,
            self.item_missed_call,
            None,  # Separator
            self.item_uptime,
            self.item_traffic,
            None,  # Separator
            self.item_open_dashboard,
            self.item_open_modem,
            self.item_refresh,
            None,  # Separator
            self.item_quit,
        ]

        # Start local web dashboard server in background daemon thread
        self.start_web_server()

        # Initial check
        self.check_modem_status()
        self.check_sms_and_calls()

        # Schedule recurring background timer
        self.timer = rumps.Timer(self.timer_tick, CHECK_INTERVAL_SECONDS)
        self.timer.start()

    def start_web_server(self):
        def _run():
            try:
                web_dashboard.run_server()
            except Exception as e:
                print(f"[DashboardServer] Error: {e}", file=sys.stderr)

        t = threading.Thread(target=_run, daemon=True)
        t.start()

    def check_modem_status(self):
        data = self.client.get_status()

        if not data:
            self.is_connected = False
            self.title = "📶 آفلاین"
            self.item_status.title = "  وضعیت ارتباط: 🔴 آفلاین (مودم در دسترس نیست)"
            self.item_battery.title = "  باتری: قطع ارتباط"
            self.item_signal.title = "  کیفیت آنتن: --"
            self.item_speed.title = "  سرعت تبادل داده: --"
            self.item_clients.title = "  دستگاه‌های متصل: --"
            self.item_sms.title = "  صندوق پیامک‌ها: --"
            self.item_uptime.title = "  مدت روشن بودن: --"
            self.item_traffic.title = "  حجم تبادل کل: --"
            return

        self.is_connected = True
        self.item_status.title = "  وضعیت ارتباط: 🟢 آنلاین و متصل"

        # Battery percentage & charging state
        try:
            battery_percent = int(data.get("battery_percent", 0))
        except (ValueError, TypeError):
            battery_percent = 0

        is_charging = str(data.get("battery_charging", "0")) == "1"
        fa_batt = fa_num(battery_percent)
        gauge = format_gauge(battery_percent)

        # Wi-Fi clients
        wifi_clients = data.get("wifi_clients_num", "0")
        try:
            w_int = int(wifi_clients)
            if w_int == 0:
                clients_text = "هیچ دستگاهی متصل نیست"
            else:
                clients_text = f"{fa_num(w_int)} دستگاه فعال"
        except Exception:
            clients_text = f"{fa_num(wifi_clients)} دستگاه"

        # Signal quality
        signal_quality = data.get("signal_quality", "--")
        signal_text = format_signal(signal_quality)

        # Unread SMS
        unread_sms = data.get("unread_long", "0")
        try:
            u_int = int(unread_sms)
            if u_int == 0:
                sms_text = "بدون پیام جدید"
            else:
                sms_text = f"{fa_num(u_int)} پیامک خوانده‌نشده 🔴"
        except Exception:
            sms_text = f"{fa_num(unread_sms)} پیام جدید"

        # Speeds
        rx_speed = format_speed_fa(data.get("rx_speed", 0))
        tx_speed = format_speed_fa(data.get("tx_speed", 0))

        # Runtime & Traffic
        uptime_text = format_uptime_fa(data.get("run_seconds", 0))
        rx_traffic = format_traffic_fa(data.get("rx_byte_all", 0))
        tx_traffic = format_traffic_fa(data.get("tx_byte_all", 0))

        # Reset alert triggers if connected to charger or battery recovered
        if is_charging or battery_percent > 15:
            if self.alerted_10 or self.alerted_5:
                self.alerted_10 = False
                self.alerted_5 = False

        # Status Bar Title & Battery Item
        if is_charging:
            self.title = f"⚡ {fa_batt}٪"
            battery_text = f"  باتری: {fa_batt}٪ [{gauge}] (در حال شارژ ⚡)"
        else:
            if battery_percent <= 10:
                self.title = f"⚠️ {fa_batt}٪"
            elif battery_percent <= 20:
                self.title = f"🪫 {fa_batt}٪"
            else:
                self.title = f"🔋 {fa_batt}٪"
            battery_text = f"  باتری: {fa_batt}٪ [{gauge}] (در حال مصرف)"

        # Update Menu Titles
        self.item_battery.title = battery_text
        self.item_signal.title = f"  کیفیت آنتن: {signal_text}"
        self.item_speed.title = f"  سرعت داده: ↓ دانلود {rx_speed} | ↑ آپلود {tx_speed}"
        self.item_clients.title = f"  دستگاه‌های متصل: {clients_text}"
        self.item_sms.title = f"  صندوق پیامک‌ها: {sms_text}"
        self.item_uptime.title = f"  مدت روشن بودن: {uptime_text}"
        self.item_traffic.title = f"  مصرف کل: ↓ {rx_traffic} | ↑ {tx_traffic}"

        # Evaluate Battery Alert Triggers
        if not is_charging:
            if battery_percent <= 5 and not self.alerted_5:
                send_macos_notification(
                    title="هشدار بحرانی باتری مودم",
                    message=f"شارژ باتری مودم به {fa_batt}٪ رسیده و به زودی خاموش می‌شود! لطفاً سریعاً شارژر را متصل کنید.",
                    sound="Basso",
                )
                self.alerted_5 = True
                self.alerted_10 = True
            elif battery_percent <= 10 and not self.alerted_10:
                send_macos_notification(
                    title="هشدار کمبود شارژ مودم",
                    message=f"شارژ باتری مودم به {fa_batt}٪ رسید. لطفاً آن را به شارژر متصل کنید.",
                    sound="Sosumi",
                )
                self.alerted_10 = True

    def check_sms_and_calls(self):
        sms_data = self.client.get_sms_list(page=1, data_per_page=15)
        messages = sms_data.get("messages", [])

        if not messages:
            return

        current_ids = set()
        for m in messages:
            msg_id = m.get("id")
            current_ids.add(msg_id)

            # Check for latest missed call to display in menu
            if m.get("is_missed_call") and not self.last_missed_call:
                raw_caller = m.get("caller_number") or m.get("sender") or ""
                self.last_missed_call = raw_caller
                self.item_missed_call.title = f"  آخرین تماس بی‌پاسخ: {fa_num(raw_caller)}"

            # If not initial load, notify new arrivals
            if not self.first_sms_check and msg_id not in self.seen_sms_ids:
                if m.get("is_missed_call"):
                    caller = m.get("caller_number") or m.get("sender") or ""
                    send_macos_notification(
                        title="📞 تماس از دست رفته جدید!",
                        message=f"شما یک تماس بی‌پاسخ از {fa_num(caller)} داشته‌اید.",
                        sound="Basso",
                    )
                    self.last_missed_call = caller
                    self.item_missed_call.title = f"  آخرین تماس بی‌پاسخ: {fa_num(caller)}"
                else:
                    sender = m.get("sender") or ""
                    preview = m.get("text", "")[:70]
                    send_macos_notification(
                        title=f"💬 پیامک جدید از {fa_num(sender)}",
                        message=preview,
                        sound="Ping",
                    )

        self.seen_sms_ids.update(current_ids)
        self.first_sms_check = False

    def timer_tick(self, _):
        self.check_modem_status()
        self.check_sms_and_calls()

    def manual_refresh(self, _):
        self.check_modem_status()
        self.check_sms_and_calls()

    def open_dashboard(self, _):
        webbrowser.open(DASHBOARD_URL)

    def open_modem_panel(self, _):
        webbrowser.open(MODEM_PANEL_URL)

    def quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    app = ModemBatteryApp()
    app.run()
