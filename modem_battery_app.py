#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modem Monitor, Menu Bar Widget & SMS/Call Center for macOS
- Battery percentage in macOS Menu Bar with <= 10% alerts
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

CHECK_INTERVAL_SECONDS = 45
DASHBOARD_URL = "http://127.0.0.1:8080"


def format_speed(bps_str):
    try:
        b = float(bps_str)
        if b < 1024:
            return f"{b:.0f} B/s"
        elif b < 1024 * 1024:
            return f"{b / 1024:.1f} KB/s"
        else:
            return f"{b / (1024 * 1024):.2f} MB/s"
    except Exception:
        return "0 B/s"


def send_macos_notification(title: str, message: str, sound: str = "Ping"):
    safe_title = title.replace('"', '\\"')
    safe_msg = message.replace('"', '\\"')
    script = f'display notification "{safe_msg}" with title "{safe_title}" sound name "{sound}"'
    try:
        subprocess.run(["osascript", "-e", script], check=False)
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
        
        # Setup menu items
        self.item_model = rumps.MenuItem("مودم: NWR-945X")
        self.item_model.set_callback(None)
        
        self.item_battery = rumps.MenuItem("درصد باتری: در حال بررسی...")
        self.item_battery.set_callback(None)
        
        self.item_clients = rumps.MenuItem("دستگاه‌های متصل: --")
        self.item_clients.set_callback(None)
        
        self.item_signal = rumps.MenuItem("کیفیت سیگنال: --")
        self.item_signal.set_callback(None)
        
        self.item_sms = rumps.MenuItem("پیامک‌های خوانده‌نشده: --")
        self.item_sms.set_callback(None)
        
        self.item_missed_call = rumps.MenuItem("آخرین تماس بی‌پاسخ: --")
        self.item_missed_call.set_callback(None)
        
        self.item_speed = rumps.MenuItem("سرعت اینترنت: --")
        self.item_speed.set_callback(None)
        
        # Action items
        self.item_open_dashboard = rumps.MenuItem("💬 صندوق پیامک‌ها و پنل مدیریت (وب)", callback=self.open_dashboard)
        self.item_refresh = rumps.MenuItem("بروزرسانی وضعیت", callback=self.manual_refresh)
        self.item_open_modem = rumps.MenuItem("باز کردن پنل اصلی مودم (۱۹۲.۱۶۸.۱.۱)", callback=self.open_modem_panel)
        self.item_quit = rumps.MenuItem("خروج", callback=self.quit_app)
        
        # Build menu hierarchy
        self.menu = [
            self.item_model,
            None,  # Separator
            self.item_battery,
            self.item_signal,
            self.item_clients,
            self.item_sms,
            self.item_missed_call,
            self.item_speed,
            None,  # Separator
            self.item_open_dashboard,
            self.item_refresh,
            self.item_open_modem,
            None,  # Separator
            self.item_quit
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
            self.item_battery.title = "وضعیت: مودم در دسترس نیست"
            self.item_clients.title = "دستگاه‌های متصل: --"
            self.item_signal.title = "کیفیت سیگنال: --"
            self.item_sms.title = "پیامک‌های خوانده‌نشده: --"
            self.item_speed.title = "سرعت اینترنت: --"
            return

        self.is_connected = True
        
        try:
            battery_percent = int(data.get("battery_percent", 0))
        except (ValueError, TypeError):
            battery_percent = 0
            
        is_charging = str(data.get("battery_charging", "0")) == "1"
        wifi_clients = data.get("wifi_clients_num", "--")
        signal_quality = data.get("signal_quality", "--")
        unread_sms = data.get("unread_long", "0")
        rx_speed = format_speed(data.get("rx_speed", 0))
        tx_speed = format_speed(data.get("tx_speed", 0))

        # Reset alert triggers if connected to charger or battery recovered
        if is_charging or battery_percent > 15:
            if self.alerted_10 or self.alerted_5:
                self.alerted_10 = False
                self.alerted_5 = False

        # Status Bar Title & Icon
        if is_charging:
            self.title = f"⚡ {battery_percent}%"
            battery_text = f"درصد باتری: {battery_percent}٪ (در حال شارژ ⚡)"
        else:
            if battery_percent <= 10:
                self.title = f"⚠️ {battery_percent}%"
            elif battery_percent <= 20:
                self.title = f"🪫 {battery_percent}%"
            else:
                self.title = f"🔋 {battery_percent}%"
            battery_text = f"درصد باتری: {battery_percent}٪ (در حال مصرف)"

        # Update menu items
        self.item_battery.title = battery_text
        self.item_clients.title = f"دستگاه‌های متصل: {wifi_clients}"
        self.item_signal.title = f"کیفیت سیگنال: {signal_quality} از ۵"
        self.item_sms.title = f"پیامک‌های خوانده‌نشده: {unread_sms}"
        self.item_speed.title = f"سرعت: دانلود {rx_speed} | آپلود {tx_speed}"

        # Evaluate Battery Alert Triggers
        if not is_charging:
            if battery_percent <= 5 and not self.alerted_5:
                send_macos_notification(
                    title="هشدار بحرانی باتری مودم",
                    message=f"شارژ باتری مودم به {battery_percent}٪ رسیده و به زودی خاموش می‌شود! لطفاً سریعاً شارژر را متصل کنید.",
                    sound="Basso"
                )
                self.alerted_5 = True
                self.alerted_10 = True
            elif battery_percent <= 10 and not self.alerted_10:
                send_macos_notification(
                    title="هشدار کمبود شارژ مودم",
                    message=f"شارژ باتری مودم به {battery_percent}٪ رسید. لطفاً آن را به شارژر متصل کنید.",
                    sound="Sosumi"
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
                self.last_missed_call = m.get("caller_number") or m.get("sender")
                self.item_missed_call.title = f"آخرین تماس بی‌پاسخ: {self.last_missed_call}"

            # If not initial load, notify new arrivals
            if not self.first_sms_check and msg_id not in self.seen_sms_ids:
                if m.get("is_missed_call"):
                    caller = m.get("caller_number") or m.get("sender")
                    send_macos_notification(
                        title="📞 تماس از دست رفته جدید!",
                        message=f"شما یک تماس بی‌پاسخ از {caller} داشته‌اید.",
                        sound="Basso"
                    )
                    self.last_missed_call = caller
                    self.item_missed_call.title = f"آخرین تماس بی‌پاسخ: {caller}"
                else:
                    sender = m.get("sender")
                    preview = m.get("text", "")[:70]
                    send_macos_notification(
                        title=f"💬 پیامک جدید از {sender}",
                        message=preview,
                        sound="Ping"
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
        webbrowser.open("http://192.168.1.1")

    def quit_app(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    app = ModemBatteryApp()
    app.run()
