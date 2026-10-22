#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI Tool to manage SMS, Missed Calls, and USSD on NWR-945X Modem
With Solar Hijri / Shamsi date formatting & Read Status synchronization.

Usage:
  ./sms.py inbox [limit] [--mark-read]
  ./sms.py read <id>
  ./sms.py mark-read <id | --all>
  ./sms.py send <phone> "<message>"
  ./sms.py calls
  ./sms.py ussd "<code>"
  ./sms.py delete <id>
"""

import sys
from modem_client import ModemClient


def print_banner():
    print("=" * 65)
    print("📱 سامانه مدیریت پیامک و تماس مودم NWR-945X (تاریخ شمسی)")
    print("=" * 65)


def cmd_inbox(client: ModemClient, limit: int = 10, auto_mark_read: bool = False):
    print_banner()
    res = client.get_sms_list(page=1, data_per_page=limit, box="inbox")
    messages = res.get("messages", [])
    if not messages:
        print("صندوق پیامک‌ها خالی است یا مودم در دسترس نیست.")
        return
        
    print(f"تعداد کل پیامک‌ها: {res.get('total_messages', len(messages))}\n")
    for idx, m in enumerate(messages, 1):
        status_tag = "🔴 [جدید / خوانده‌نشده]" if m["is_unread"] else "⚪️ [خوانده‌شده]"
        if m["is_missed_call"]:
            call_tag = f" 📞 [تماس بی‌پاسخ از {m['caller_number'] or 'ناشناس'}]"
        else:
            call_tag = ""
            
        print(f"{idx}. {status_tag}{call_tag} فرستنده: {m['sender']}")
        print(f"   📅 تاریخ و زمان (شمسی): {m['time']}")
        print(f"   شناسه پیامک: {m['id']}")
        print(f"   متن: {m['text']}")
        print("-" * 65)
        
        if auto_mark_read and m["is_unread"]:
            client.mark_sms_as_read(m["id"])


def cmd_read(client: ModemClient, msg_id: str):
    print_banner()
    res = client.get_sms_list(page=1, data_per_page=50, box="inbox")
    found = None
    for m in res.get("messages", []):
        if msg_id in m["id"] or m["id"] == msg_id:
            found = m
            break
            
    if not found:
        print(f"پیامکی با شناسه {msg_id} یافت نشد.")
        return
        
    print(f"فرستنده: {found['sender']}")
    print(f"تاریخ شمسی: {found['time']}")
    print(f"متن کامل:\n{found['text']}\n")
    
    if found["is_unread"]:
        if client.mark_sms_as_read(found["id"]):
            print("✅ وضعیت پیامک در مودم به «خوانده‌شده» تغییر یافت.")


def cmd_mark_read(client: ModemClient, target: str):
    print_banner()
    if target in ("--all", "all"):
        res = client.get_sms_list(page=1, data_per_page=50, box="inbox")
        count = 0
        for m in res.get("messages", []):
            if m["is_unread"]:
                if client.mark_sms_as_read(m["id"]):
                    count += 1
        print(f"✅ تعداد {count} پیامک خوانده‌نشده در مودم به «خوانده‌شده» تغییر یافتند.")
    else:
        if client.mark_sms_as_read(target):
            print(f"✅ پیامک {target} با موفقیت در مودم خوانده شد.")
        else:
            print(f"❌ خطا در تغییر وضعیت پیامک {target}.")


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
        print(f"   زمان دریافت (شمسی): {c['time']}")
        print(f"   متن پیامک اپراتور: {c['text']}")
        print("-" * 65)


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
    print("-" * 45)
    print(response)
    print("-" * 45)


def cmd_delete(client: ModemClient, msg_id: str):
    print_banner()
    print(f"در حال حذف پیامک {msg_id} ...")
    if client.delete_sms(msg_id):
        print("✅ پیامک با موفقیت حذف شد.")
    else:
        print("❌ خطا در حذف پیامک.")


def show_help():
    print("""
راهنمای ابزار پیامک مودم (با تاریخ شمسی):
  ./sms.py inbox [تعداد] [--mark-read]   نمایش پیامک‌های دریافتی به تاریخ شمسی
  ./sms.py read <شناسه>                 مشاهده پیامک و تغییر وضعیت به خوانده‌شده در مودم
  ./sms.py mark-read <شناسه | --all>    علامت‌گذاری پیامک(ها) به عنوان خوانده‌شده
  ./sms.py send <شماره> "<متن>"         ارسال پیامک جدید
  ./sms.py calls                        نمایش فهرست تماس‌های بی‌پاسخ به تاریخ شمسی
  ./sms.py ussd "<code>"                شماره‌گیری کدهای دستوری
  ./sms.py delete <شناسه>               حذف یک پیامک
""")


def main():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(0)
        
    client = ModemClient()
    cmd = sys.argv[1].lower()
    
    if cmd in ("inbox", "list"):
        limit = 10
        auto_mark = "--mark-read" in sys.argv
        for arg in sys.argv[2:]:
            if arg.isdigit():
                limit = int(arg)
        cmd_inbox(client, limit, auto_mark)
    elif cmd == "read":
        if len(sys.argv) < 3:
            print("خطا: شناسه پیامک را وارد کنید.")
            sys.exit(1)
        cmd_read(client, sys.argv[2])
    elif cmd in ("mark-read", "markread"):
        target = sys.argv[2] if len(sys.argv) > 2 else "--all"
        cmd_mark_read(client, target)
    elif cmd == "calls":
        cmd_calls(client)
    elif cmd == "send":
        if len(sys.argv) < 4:
            print("خطا: شماره گیرنده و متن پیامک را وارد کنید.")
            sys.exit(1)
        cmd_send(client, sys.argv[2], sys.argv[3])
    elif cmd == "ussd":
        if len(sys.argv) < 3:
            print("خطا: کد دستوری را وارد کنید.")
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
