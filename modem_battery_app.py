#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modem Monitor & Status Widget for macOS Menu Bar
Minimalist, clean English UI with real-time telemetry, SMS & missed call alerts.
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


def format_gauge(percent: int, length: int = 8) -> str:
    """ASCII progress bar like [███░░░░░]."""
    clamped = max(0, min(100, int(percent)))
    filled = int(round(length * (clamped / 100.0)))
    return "█" * filled + "░" * (length - filled)


def format_signal(sig_val) -> str:
    """Format signal quality into a clean '5/5 (Excellent)  ▂▄▆█'."""
    try:
        s = int(sig_val)
    except (ValueError, TypeError):
        return "--"

    bars_map = ["░░░░", " ▂░░", " ▂▄░", " ▂▄▆", " ▂▄▆█", " ▂▄▆█"]
    bars = bars_map[min(max(0, s), 5)]
    labels = {
        0: "No Signal",
        1: "Very Weak",
        2: "Weak",
        3: "Fair",
        4: "Good",
        5: "Excellent",
    }
    label = labels.get(s, "")
    return f"{s}/5 ({label}) {bars}"


def format_speed(bps_val) -> str:
    """Format bps into B/s, KB/s, or MB/s."""
    try:
        b = float(bps_val)
        if b < 1024:
            return f"{int(b)} B/s"
        elif b < 1024 * 1024:
            kb = b / 1024.0
            return f"{kb:.1f} KB/s" if kb < 100 else f"{int(kb)} KB/s"
        else:
            mb = b / (1024.0 * 1024.0)
            return f"{mb:.2f} MB/s"
    except Exception:
        return "0 B/s"


def format_uptime(seconds_val) -> str:
    """Format seconds into concise hours and minutes."""
    try:
        sec = int(seconds_val)
        hours = sec // 3600
        mins = (sec % 3600) // 60
        if hours > 0:
            return f"{hours}h {mins}m"
        return f"{mins}m"
    except Exception:
        return "--"


def format_traffic_summary(rx_bytes, tx_bytes) -> str:
    """Format total network data usage into GB."""
    try:
        rx_gb = float(rx_bytes) / (1024.0 ** 3)
        tx_gb = float(tx_bytes) / (1024.0 ** 3)
        return f"↓ {rx_gb:.1f} GB  •  ↑ {tx_gb:.1f} GB"
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
        super(ModemBatteryApp, self).__init__("Modem", title="🔋 ...", quit_button=None)

        self.client = ModemClient()

        # State tracking
        self.alerted_10 = False
        self.alerted_5 = False
        self.is_connected = False

        # SMS & Missed Call tracking
        self.seen_sms_ids = set()
        self.first_sms_check = True
        self.last_missed_call = None

        # Build Clean Minimalist Menu
        # 1. Header & Status
        self.item_header = rumps.MenuItem("NWR-945X Modem  •  Connecting...", callback=None)

        # 2. Battery & Power
        self.item_battery = rumps.MenuItem("Battery: Checking...", callback=None)

        # 3. Network & Signal
        self.item_signal = rumps.MenuItem("Signal: --", callback=None)
        self.item_speed = rumps.MenuItem("Speed: --", callback=None)
        self.item_clients = rumps.MenuItem("Connected Devices: --", callback=None)

        # 4. SMS & Call Center
        self.item_sms = rumps.MenuItem("Messages: Checking...", callback=None)
        self.item_missed_call = rumps.MenuItem("Last Missed Call: None", callback=None)

        # 5. Telemetry
        self.item_uptime = rumps.MenuItem("Uptime: --  •  Data: --", callback=None)

        # 6. Actions
        self.item_open_dashboard = rumps.MenuItem("Open SMS & Web Dashboard", callback=self.open_dashboard)
        self.item_open_modem = rumps.MenuItem("Modem Admin Panel (192.168.1.1)", callback=self.open_modem_panel)
        self.item_refresh = rumps.MenuItem("Refresh Status", callback=self.manual_refresh)
        self.item_quit = rumps.MenuItem("Quit", callback=self.quit_app)

        # Menu Layout
        self.menu = [
            self.item_header,
            None,  # Separator
            self.item_battery,
            self.item_signal,
            self.item_speed,
            self.item_clients,
            None,  # Separator
            self.item_sms,
            self.item_missed_call,
            self.item_uptime,
            None,  # Separator
            self.item_open_dashboard,
            self.item_open_modem,
            self.item_refresh,
            None,  # Separator
            self.item_quit,
        ]

        # Start background local web dashboard
        self.start_web_server()

        # Initial check
        self.check_modem_status()
        self.check_sms_and_calls()

        # Recurring background timer
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
            self.title = "📶 Offline"
            self.item_header.title = "NWR-945X Modem  •  ● Offline"
            self.item_battery.title = "Battery: Disconnected"
            self.item_signal.title = "Signal: --"
            self.item_speed.title = "Speed: --"
            self.item_clients.title = "Connected Devices: --"
            self.item_sms.title = "Messages: --"
            self.item_uptime.title = "Uptime: --"
            return

        self.is_connected = True
        self.item_header.title = "NWR-945X Modem  •  ● Online"

        # Battery
        try:
            battery_percent = int(data.get("battery_percent", 0))
        except (ValueError, TypeError):
            battery_percent = 0

        is_charging = str(data.get("battery_charging", "0")) == "1"
        gauge = format_gauge(battery_percent)

        if is_charging:
            self.title = f"⚡ {battery_percent}%"
            battery_text = f"Battery: {battery_percent}% [{gauge}] (Charging ⚡)"
        else:
            if battery_percent <= 10:
                self.title = f"⚠️ {battery_percent}%"
            elif battery_percent <= 20:
                self.title = f"🪫 {battery_percent}%"
            else:
                self.title = f"🔋 {battery_percent}%"
            battery_text = f"Battery: {battery_percent}% [{gauge}] (Discharging)"

        # Reset alert triggers if connected to charger or battery recovered
        if is_charging or battery_percent > 15:
            if self.alerted_10 or self.alerted_5:
                self.alerted_10 = False
                self.alerted_5 = False

        # Wi-Fi clients
        wifi_clients = data.get("wifi_clients_num", "0")
        try:
            w_int = int(wifi_clients)
            devices_text = f"Connected Devices: {w_int}"
        except Exception:
            devices_text = f"Connected Devices: {wifi_clients}"

        # Signal quality
        signal_quality = data.get("signal_quality", "--")
        signal_text = format_signal(signal_quality)

        # Speeds
        rx_speed = format_speed(data.get("rx_speed", 0))
        tx_speed = format_speed(data.get("tx_speed", 0))

        # Unread SMS
        unread_sms = data.get("unread_long", "0")
        try:
            u_int = int(unread_sms)
            sms_text = "Messages: 0 Unread" if u_int == 0 else f"Messages: {u_int} Unread 🔴"
        except Exception:
            sms_text = f"Messages: {unread_sms}"

        # Telemetry
        uptime_str = format_uptime(data.get("run_seconds", 0))
        traffic_str = format_traffic_summary(data.get("rx_byte_all", 0), data.get("tx_byte_all", 0))

        # Update Menu Items
        self.item_battery.title = battery_text
        self.item_signal.title = f"Signal: {signal_text}"
        self.item_speed.title = f"Speed: ↓ {rx_speed}  •  ↑ {tx_speed}"
        self.item_clients.title = devices_text
        self.item_sms.title = sms_text
        self.item_uptime.title = f"Uptime: {uptime_str}  •  Data: {traffic_str}"

        # Evaluate Battery Alert Triggers
        if not is_charging:
            if battery_percent <= 5 and not self.alerted_5:
                send_macos_notification(
                    title="Modem Battery Critical",
                    message=f"Modem battery reached {battery_percent}%! Please plug in charger immediately.",
                    sound="Basso",
                )
                self.alerted_5 = True
                self.alerted_10 = True
            elif battery_percent <= 10 and not self.alerted_10:
                send_macos_notification(
                    title="Modem Battery Low",
                    message=f"Modem battery is at {battery_percent}%. Please connect to power.",
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

            if m.get("is_missed_call") and not self.last_missed_call:
                caller = m.get("caller_number") or m.get("sender") or "Unknown"
                self.last_missed_call = caller
                self.item_missed_call.title = f"Last Missed Call: {caller}"

            # New notifications
            if not self.first_sms_check and msg_id not in self.seen_sms_ids:
                if m.get("is_missed_call"):
                    caller = m.get("caller_number") or m.get("sender") or "Unknown"
                    send_macos_notification(
                        title="📞 New Missed Call",
                        message=f"Missed call from {caller}",
                        sound="Basso",
                    )
                    self.last_missed_call = caller
                    self.item_missed_call.title = f"Last Missed Call: {caller}"
                else:
                    sender = m.get("sender") or "Unknown"
                    preview = m.get("text", "")[:70]
                    send_macos_notification(
                        title=f"💬 New SMS from {sender}",
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
