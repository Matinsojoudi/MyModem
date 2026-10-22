#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import json
import sys

URL = "http://192.168.1.1/xml_action.cgi?method=get&module=duster&file=json_status_info"

try:
    r = requests.get(URL, timeout=3)
    if r.status_code == 200:
        d = r.json()
        battery = d.get('battery_percent', '?')
        charging = "بله ⚡" if d.get('battery_charging') == '1' else "خیر (در حال مصرف)"
        wifi_clients = d.get('wifi_clients_num', '?')
        signal = d.get('signal_quality', '?')
        sms = d.get('unread_long', '0')
        rx_speed = d.get('rx_speed', '0')
        tx_speed = d.get('tx_speed', '0')
        
        print("=" * 45)
        print("📡 وضعیت زنده مودم NWR-945X")
        print("=" * 45)
        print(f"🔋 درصد شارژ باتری: {battery}%")
        print(f"⚡ متصل به شارژر: {charging}")
        print(f"📶 کیفیت سیگنال: {signal} از ۵")
        print(f"👥 تعداد دستگاه‌های متصل: {wifi_clients}")
        print(f"✉️  پیامک‌های خوانده‌نشده: {sms}")
        print(f"⬇️  سرعت دانلود: {int(rx_speed)/1024:.1f} KB/s")
        print(f"⬆️  سرعت آپلود: {int(tx_speed)/1024:.1f} KB/s")
        print("=" * 45)
    else:
        print(f"خطا در دریافت پاسخ: کد {r.status_code}")
except Exception as e:
    print(f"عدم دسترسی به مودم: {e}")
