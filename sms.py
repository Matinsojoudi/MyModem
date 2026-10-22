#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Tool to manage SMS, Missed Calls, and USSD on NWR-945X Modem
Usage:
  ./sms.py inbox [limit]
  ./sms.py send <phone> "<message>"
  ./sms.py calls
  ./sms.py ussd "<code>"
  ./sms.py delete <id>
"""

import sys
from modem_client import ModemClient


def print_banner():
    print("=" * 60)
    print("📱 سامانه مدیریت پیامک و تماس مودم NWR-945X")
    print("=" * 60)


def cmd_inbox(client: ModemClient, limit: int = 10):
    print_banner()
    res = client.get_sms_list(page=1, data_per_page=limit, box="inbox")
    messages = res.get("messages", [])
    if not messages:
        print("صندوق پیامک‌ها خالی است یا مودم در دسترس نیست.")
        return
        
    print(f"تعداد کل پیامک‌ها: {res.get('total_messages', len(messages))}\n")
    for idx, m in enumerate(messages, 1):
        status_tag = "🔴 [خوانده‌نشده]" if m["is_unread"] else "⚪️ [خوانده‌شده]"
        if m["is_missed_call"]:
            call_tag = f" 📞 [تماس بی‌پاسخ از {m['caller_number'] or 'ناشناس'}]"
        else:
            call_tag = ""
            
        print(f"{idx}. {status_tag}{call_tag} فرستنده: {m['sender']} | تاریخ: {m['time']}")
        print(f"   شناسه: {m['id']}")
        print(f"   متن: {m['text']}")
        print("-" * 60)


def cmd_calls(client: ModemClient):
    print_banner()
    print("📞 گزارش تماس‌های از دست رفته (بر اساس پیامک‌های اپراتور):\n")
    res = client.get_sms_list(page=1, data_per_page=50, box="inbox")
    calls = [m for m in res.get("messages", []) if m["is_missed_call"]]
    
    if not calls:
        print("هیچ تماس بی‌پاسخی در پیامک‌ها یافت نشد.")
        return
        
    for idx, c in enumerate(calls, 1):
        print(f"{idx}. شماره تماس‌گیرنده: {c['caller_number'] or c['sender']}")
        print(f"   زمان دریافت گزارش: {c['time']}")
        print(f"   متن کامل پیامک: {c['text']}")
        print("-" * 60)


def cmd_send(client: ModemClient, phone: str, text: str):
    print_banner()
    print(f"در حال ارسال پیامک به: {phone}")
    print(f"متن پیامک:\n{text}\n")
    success = client.send_sms(phone, text)
    if success:
        print("✅ پیامک با موفقیت به مودم ارسال و به شبکه فرستاده شد.")
    else:
        print("❌ خطا در ارسال پیامک. لطفاً شارژ سیم‌کارت و اتصال مودم را بررسی کنید.")


def cmd_ussd(client: ModemClient, code: str):
    print_banner()
    print(f"در حال شماره‌گیری کد دستوری {code} ...")
    response = client.send_ussd(code)
    print("\n📩 پاسخ دریافتی از اپراتور:")
    print("-" * 40)
    print(response)
    print("-" * 40)


def cmd_delete(client: ModemClient, msg_id: str):
    print_banner()
    print(f"در حال حذف پیامک {msg_id} ...")
    if client.delete_sms(msg_id):
        print("✅ پیامک با موفقیت حذف شد.")
    else:
        print("❌ خطا در حذف پیامک.")


def show_help():
    print("""
راهنمای استفاده از ابزار پیامک مودم:
  ./sms.py inbox [تعداد]           نمایش پیامک‌های دریافتی (پیش‌فرض ۱۰ تا)
  ./sms.py send <شماره> "<متن>"   ارسال پیامک جدید
  ./sms.py calls                  نمایش فهرست تماس‌های بی‌پاسخ
  ./sms.py ussd "<code>"          اجرای کدهای دستوری (مثل *100# یا *1#)
  ./sms.py delete <شناسه>         حذف یک پیامک
""")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)
        
    client = ModemClient()
    cmd = sys.argv[1].lower()
    
    if cmd in ("inbox", "list"):
        limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
        cmd_inbox(client, limit)
    elif cmd == "calls":
        cmd_calls(client)
    elif cmd == "send":
        if len(sys.argv) < 4:
            print("خطا: شماره گیرنده و متن پیامک را وارد کنید.")
            print("مثال: ./sms.py send 09123456789 \"سلام وقت بخیر\"")
            sys.exit(1)
        cmd_send(client, sys.argv[2], sys.argv[3])
    elif cmd == "ussd":
        if len(sys.argv) < 3:
            print("خطا: کد دستوری را وارد کنید.")
            print("مثال: ./sms.py ussd \"*100#\"")
            sys.exit(1)
        cmd_ussd(client, sys.argv[2])
    elif cmd in ("delete", "del", "rm"):
        if len(sys.argv) < 3:
            print("خطا: شناسه پیامک را وارد کنید.")
            sys.exit(1)
        cmd_delete(client, sys.argv[2])
    else:
        show_help()


if __name__ == "__main__":
    main()
