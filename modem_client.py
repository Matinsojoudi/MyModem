#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core API Client for NWR-945X 4G Portable Wi-Fi Modem
Provides methods for:
- Modem status & battery telemetry
- SMS reading (both Local and SIM Card storage), decoding, sending, deleting, and marking as read
- Solar/Jalali (هجری شمسی) date conversion in Iran/Tehran time
- Missed call detection
- USSD code dialing with proper network error handling
- Device reboot
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

MODEM_IP = "192.168.1.1"
BASE_URL = f"http://{MODEM_IP}/xml_action.cgi"

PERSIAN_MONTHS = [
    "", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
    "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"
]


def gregorian_to_jalali(gy: int, gm: int, gd: int):
    """Accurate Gregorian to Jalali (Solar Hijri) date conversion."""
    g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    if gy > 1600:
        jy = 979
        gy -= 1600
    else:
        jy = 0
        gy -= 621
    gy2 = gy if gm > 2 else gy - 1
    days = 365 * gy + int((gy2 + 3) / 4) - int((gy2 + 99) / 100) + int((gy2 + 399) / 400) - 80 + gd + g_d_m[gm - 1]
    jy += 33 * int(days / 12053)
    days %= 12053
    jy += 4 * int(days / 1461)
    days %= 1461
    if days > 365:
        jy += int((days - 1) / 365)
        days = (days - 1) % 365
    if days < 186:
        jm = 1 + int(days / 31)
        jd = 1 + (days % 31)
    else:
        jm = 7 + int((days - 186) / 30)
        jd = 1 + ((days - 186) % 30)
    return jy, jm, jd


def parse_modem_time_to_shamsi(raw_time: str) -> str:
    """
    Parses modem timestamp (e.g. '26,10,03,19,06,11,+3')
    into Shamsi (Persian) format: '۱۱ مهر ۱۴۰۵ - ساعت ۱۹:۰۶'
    """
    if not raw_time:
        return "--"
    try:
        parts = [p.strip() for p in raw_time.split(",")]
        if len(parts) >= 6:
            gy = 2000 + int(parts[0])
            gm = int(parts[1])
            gd = int(parts[2])
            hour = int(parts[3])
            minute = int(parts[4])
            second = int(parts[5])

            jy, jm, jd = gregorian_to_jalali(gy, gm, gd)
            month_name = PERSIAN_MONTHS[jm]
            return f"{jd} {month_name} {jy} - ساعت {hour:02d}:{minute:02d}"
    except Exception:
        pass
    return raw_time


def uni_decode(hex_str: str) -> str:
    """Decodes UCS2 / UTF-16BE hex string from modem into Python string."""
    if not hex_str:
        return ""
    try:
        clean_hex = hex_str.strip()
        if len(clean_hex) % 2 != 0:
            clean_hex = clean_hex[:-1]
        raw_bytes = bytes.fromhex(clean_hex)
        return raw_bytes.decode("utf-16-be", errors="replace")
    except Exception:
        return hex_str


def uni_encode(text: str) -> str:
    """Encodes Python string into UTF-16BE uppercase hex string for modem."""
    if not text:
        return ""
    return text.encode("utf-16-be").hex().upper()


def get_sms_time_str() -> str:
    """Generates modem time format: YY,MM,DD,HH,MM,SS,+TZ"""
    now = datetime.now()
    return now.strftime("%y,%m,%d,%H,%M,%S,+3.5")


def normalize_phone(phone: str) -> str:
    """Normalizes Iranian phone numbers (e.g. +98912..., 0098912..., 98912..., 912... -> 0912...)."""
    if not phone:
        return ""
    import re
    clean = re.sub(r'[\s\-\(\)\.\+]', '', str(phone)).lstrip(';')
    if clean.startswith('98') and len(clean) >= 12:
        clean = '0' + clean[2:]
    elif clean.startswith('0098'):
        clean = '0' + clean[4:]
    elif len(clean) == 10 and clean.startswith('9'):
        clean = '0' + clean
    return clean


class ModemClient:
    def __init__(self, ip: str = MODEM_IP, timeout: float = 3.5):
        self.ip = ip
        self.base_url = f"http://{ip}/xml_action.cgi"
        self.timeout = timeout

    def get_status(self) -> Optional[Dict[str, Any]]:
        """Fetches live modem status (battery, network, clients, unread count)."""
        url = f"{self.base_url}?method=get&module=duster&file=json_status_info{int(time.time()*1000)}"
        try:
            r = requests.get(url, timeout=self.timeout)
            if r.status_code == 200:
                return r.json()
        except Exception as e:
            print(f"[ModemClient] get_status error: {e}")
        return None

    def get_sms_list(self, page: int = 1, data_per_page: int = 50, box: str = "inbox") -> Dict[str, Any]:
        """
        Fetches and decodes SMS messages from both local device and SIM card memory.
        Merges and sorts all messages chronologically.
        """
        url = f"{self.base_url}?method=post&module=duster&file=json_message_set{int(time.time()*1000)}"
        
        all_raw_messages = []
        
        if box == "inbox":
            # 1. Fetch Local Device Inbox
            try:
                r_local = requests.post(
                    url,
                    json={"message_flag": "GET_RCV_SMS_LOCAL", "page_number": 1, "data_per_page": str(data_per_page)},
                    timeout=self.timeout
                )
                if r_local.status_code == 200:
                    all_raw_messages.extend(r_local.json().get("message_list", []))
            except Exception as e:
                print(f"[ModemClient] Fetch local SMS error: {e}")

            # 2. Fetch SIM Card Inbox
            try:
                r_sim = requests.post(
                    url,
                    json={"message_flag": "GET_SIM_SMS", "page_number": 1, "data_per_page": str(data_per_page)},
                    timeout=self.timeout
                )
                if r_sim.status_code == 200:
                    all_raw_messages.extend(r_sim.json().get("message_list", []))
            except Exception as e:
                print(f"[ModemClient] Fetch SIM SMS error: {e}")
        else:
            # Outbox
            try:
                r_sent = requests.post(
                    url,
                    json={"message_flag": "GET_SENT_SMS_LOCAL", "page_number": 1, "data_per_page": str(data_per_page)},
                    timeout=self.timeout
                )
                if r_sent.status_code == 200:
                    all_raw_messages.extend(r_sent.json().get("message_list", []))
            except Exception as e:
                print(f"[ModemClient] Fetch sent SMS error: {e}")

        # Deduplicate by message ID / index
        seen_ids = set()
        unique_raw = []
        for m in all_raw_messages:
            idx = m.get("index")
            if idx and idx not in seen_ids:
                seen_ids.add(idx)
                unique_raw.append(m)

        # Sort descending by received timestamp (newest first)
        unique_raw.sort(key=lambda x: x.get("received", ""), reverse=True)

        decoded_messages = []
        unread_count = 0
        for item in unique_raw:
            sender = uni_decode(item.get("from", "")).lstrip(";")
            text = uni_decode(item.get("subject", ""))
            recv_time_raw = item.get("received", "")
            recv_time_shamsi = parse_modem_time_to_shamsi(recv_time_raw)
            status = str(item.get("status", "1"))  # In this modem: "0" = unread, "1" = read
            msg_id = item.get("index", "")
            
            is_unread = (status == "0")
            if is_unread:
                unread_count += 1
            
            # Detect missed call SMS from operator
            is_missed_call = False
            caller_number = ""
            if "تماس از دست رفته" in text or "تماس ازدست رفته" in text or "missed call" in text.lower():
                is_missed_call = True
                for word in text.split():
                    clean_word = word.strip(".,;:\"'()[]{}")
                    if clean_word.startswith("+98") or (clean_word.startswith("09") and len(clean_word) >= 11):
                        caller_number = clean_word
                        break

            storage_type = "SIM" if "SRCV" in msg_id else "دستگاه"

            decoded_messages.append({
                "id": msg_id,
                "sender": sender,
                "text": text,
                "time": recv_time_shamsi,
                "raw_time": recv_time_raw,
                "is_unread": is_unread,
                "status": status,
                "storage": storage_type,
                "is_missed_call": is_missed_call,
                "caller_number": caller_number
            })

        return {
            "messages": decoded_messages,
            "page_number": page,
            "total_pages": 1,
            "total_messages": len(decoded_messages),
            "unread_count": unread_count
        }

    def mark_sms_as_read(self, msg_id: str) -> bool:
        """
        Marks an SMS as read on modem hardware (auto-detects SIM vs Device memory).
        """
        if not msg_id:
            return False
        clean_id = msg_id if msg_id.endswith(",") else f"{msg_id},"
        is_sim = "SRCV" in clean_id
        mem_store = "0" if is_sim else "1"
        tags = "" if is_sim else "12"
        
        url = f"{self.base_url}?method=post&module=duster&file=json_message_set{int(time.time()*1000)}"
        payload = {
            "message_flag": "SET_MSG_READ",
            "sms_cmd": "7",
            "tags": tags,
            "mem_store": mem_store,
            "read_message_id": clean_id
        }
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return str(data.get("sms_cmd_status_result", "")) == "3"
        except Exception as e:
            print(f"[ModemClient] mark_sms_as_read error: {e}")
        return False

    def mark_all_sms_as_read(self) -> int:
        """Marks all unread SMS messages as read on the modem."""
        sms_data = self.get_sms_list(page=1, data_per_page=50)
        messages = sms_data.get("messages", [])
        marked = 0
        for m in messages:
            if m.get("is_unread"):
                if self.mark_sms_as_read(m.get("id")):
                    marked += 1
        return marked

    def delete_sms(self, index_ids: str) -> bool:
        """Deletes SMS by index id(s) (e.g. 'SRCV49,SRCV50,' or 'LRCV14,')."""
        if not index_ids:
            return False
        if not index_ids.endswith(","):
            index_ids += ","
            
        is_sim = "SRCV" in index_ids
        mem_store = "0" if is_sim else "1"
        tags = "" if is_sim else "12"
        
        url = f"{self.base_url}?method=post&module=duster&file=json_message_set{int(time.time()*1000)}"
        payload = {
            "message_flag": "DELETE_SMS",
            "sms_cmd": "6",
            "tags": tags,
            "mem_store": mem_store,
            "delete_message_id": index_ids
        }
        
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return str(data.get("sms_cmd_status_result", "")) == "3"
        except Exception as e:
            print(f"[ModemClient] delete_sms error: {e}")
        return False

    def delete_all_sms(self) -> int:
        """Deletes all SMS messages from SIM and Device storage."""
        sms_data = self.get_sms_list(page=1, data_per_page=50)
        messages = sms_data.get("messages", [])
        if not messages:
            return 0

        sim_ids = []
        dev_ids = []
        for m in messages:
            mid = m.get("id", "")
            if not mid:
                continue
            if not mid.endswith(","):
                mid += ","
            if "SRCV" in mid:
                sim_ids.append(mid)
            else:
                dev_ids.append(mid)

        deleted = 0
        if sim_ids:
            joined_sim = "".join(sim_ids)
            if self.delete_sms(joined_sim):
                deleted += len(sim_ids)
        if dev_ids:
            joined_dev = "".join(dev_ids)
            if self.delete_sms(joined_dev):
                deleted += len(dev_ids)
        return deleted

    def send_sms(self, phone_number: str, message_text: str) -> bool:
        """Sends an SMS to one or more phone numbers (comma-separated)."""
        clean_numbers = [p.strip() for p in phone_number.replace(";", ",").split(",") if p.strip()]
        if not clean_numbers or not message_text.strip():
            return False
            
        contacts = ",".join(clean_numbers) + ","
        encoded_content = uni_encode(message_text)
        
        url = f"{self.base_url}?method=post&module=duster&file=json_message_set{int(time.time()*1000)}"
        payload = {
            "send_from_draft_id": "",
            "message_flag": "SEND_SMS",
            "sms_cmd": "4",
            "contacts": contacts,
            "content": encoded_content,
            "encode_type": "UNICODE",
            "sms_time": get_sms_time_str()
        }
        
        try:
            r = requests.post(url, json=payload, timeout=self.timeout + 5)
            if r.status_code == 200:
                data = r.json()
                # Modem returns sms_cmd_status_result as string "3" on success
                result = str(data.get("sms_cmd_status_result", ""))
                return result == "3"
        except Exception as e:
            print(f"[ModemClient] send_sms error: {e}")
        return False

    def send_ussd(self, code: str, timeout_sec: int = 8) -> str:
        """
        Sends a USSD command (e.g. '*1#') and polls for network response.
        Handles network error codes (Type 2, 3, 4).
        """
        clean_code = code.strip()
        if not clean_code.startswith("*"):
            clean_code = "*" + clean_code
        if not clean_code.endswith("#"):
            clean_code = clean_code + "#"

        # Reset / cancel any previous session first to ensure clean state
        url_cancel = f"{self.base_url}?method=post&module=duster&file=json_ussd_set{int(time.time()*1000)}"
        try:
            requests.post(url_cancel, json={"action": "2", "ussd_param": ""}, timeout=self.timeout)
        except Exception:
            pass

        time.sleep(0.4)

        url_set = f"{self.base_url}?method=post&module=duster&file=json_ussd_set{int(time.time()*1000)}"
        payload = {
            "action": "1",
            "ussd_param": clean_code
        }
        try:
            r = requests.post(url_set, json=payload, timeout=self.timeout)
            if r.status_code != 200:
                return "خطا در ارسال درخواست USSD به مودم."
        except Exception as e:
            return f"خطای ارتباط با مودم: {e}"

        # Poll ussd_info
        url_info = f"{self.base_url}?method=get&module=duster&file=json_ussd_info{int(time.time()*1000)}"
        start_time = time.time()
        time.sleep(0.8)
        
        while time.time() - start_time < timeout_sec:
            try:
                res = requests.get(url_info, timeout=self.timeout)
                if res.status_code == 200:
                    d = res.json()
                    ussd_type = str(d.get("ussd_type", ""))
                    ussd_str = d.get("ussd_str", "")

                    # If response message exists, decode and return it
                    if ussd_str and len(ussd_str) > 0:
                        return uni_decode(ussd_str)

                    # Handled states
                    if ussd_type == "2":
                        return (
                            "نشست USSD توسط دکل شبکه مخابراتی بسته شد (Session Terminated).\n\n"
                            "علت: سیم‌کارت فعال مودم «شاتل موبایل» است و مودم‌های همراه 4G LTE فاقد کانال صوتی CSFB هستند؛ "
                            "بنابراین اپراتورهای شبکه در ایران نشست‌های کدهای دستوری USSD را روی مودم‌های همراه مسدود یا فوراً خاتمه می‌دهند.\n\n"
                            "راهکار پیشنهادی: برای استعلام مانده بسته اینترنت، شارژ ریالی و تاریخ انقضا بدون نیاز به USSD، "
                            "از سامانه آنلاین «شاتل موبایل من» به نشانی https://my.shatelmobile.ir استفاده فرمایید."
                        )
                    elif ussd_type == "3":
                        return "خطای USSD: نشست توسط کلاینت یا ارتباط دیگری پاسخ داده شد."
                    elif ussd_type == "4":
                        return "خطای USSD: این کد دستوری توسط اپراتور پشتیبانی نمی‌شود."
                    elif ussd_type in ("0", "1") and not ussd_str:
                        return "درخواست USSD ارسال شد اما اپراتور متنی بازنگرداند."

            except Exception as e:
                print(f"[ModemClient] USSD poll error: {e}")

            time.sleep(1.5)
                
        return "زمان انتظار برای دریافت پاسخ USSD از سمت شبکه به پایان رسید."

    def get_phonebook(self) -> List[Dict[str, Any]]:
        """Fetches all contacts from modem phonebook (SIM + Device)."""
        url = f"{self.base_url}?method=post&module=duster&file=json_pb_set{int(time.time()*1000)}"
        payload = {
            "pb_action": "pb_get_all",
            "location": "2",
            "page_num": "1",
            "data_per_page": "100"
        }
        contacts = []
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                entries = r.json().get("pb_entries", [])
                for e in entries:
                    raw_name = e.get("pbm_name", "")
                    name = uni_decode(raw_name).strip() if raw_name else "بی‌نام"
                    number = e.get("pbm_number", "").strip()
                    loc = e.get("pbm_location", "0")
                    storage = "سیم‌کارت" if loc == "0" else "دستگاه"
                    group = e.get("pbm_group", "common")
                    group_fa = {
                        "common": "عمومی",
                        "family": "خانواده",
                        "friend": "دوستان",
                        "colleague": "همکاران"
                    }.get(group, group)
                    
                    contacts.append({
                        "id": e.get("pbm_id"),
                        "name": name,
                        "number": number,
                        "normalized_number": normalize_phone(number),
                        "group": group_fa,
                        "storage": storage,
                        "location": loc
                    })
        except Exception as e:
            print(f"[ModemClient] get_phonebook error: {e}")
        return contacts

    def add_contact(self, name: str, number: str, group: str = "common", location: str = "0") -> bool:
        """Adds a contact to modem phonebook (location 0=SIM, 1=Device)."""
        url = f"{self.base_url}?method=post&module=duster&file=json_pb_set{int(time.time()*1000)}"
        payload = {
            "pb_action": "pbm_contact_add",
            "location": str(location),
            "name": uni_encode(name),
            "mobile": number.strip(),
            "group": group
        }
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return str(data.get("pb_result", "")) == "0"
        except Exception as e:
            print(f"[ModemClient] add_contact error: {e}")
        return False

    def delete_contact(self, contact_id: str) -> bool:
        """Deletes a contact by pbm_id from modem phonebook."""
        url = f"{self.base_url}?method=post&module=duster&file=json_pb_set{int(time.time()*1000)}"
        del_id = contact_id if contact_id.endswith(",") else f"{contact_id},"
        payload = {
            "pb_action": "pbm_contact_delete",
            "location": "2",
            "delete_option": "delete_num",
            "delete_pb_id": del_id
        }
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return str(data.get("pb_result", "")) == "0"
        except Exception as e:
            print(f"[ModemClient] delete_contact error: {e}")
        return False

    def get_sent_sms_list(self, page: int = 1, data_per_page: int = 50) -> List[Dict[str, Any]]:
        """Fetches sent SMS messages stored in modem memory."""
        url = f"{self.base_url}?method=post&module=duster&file=json_message_set{int(time.time()*1000)}"
        payload = {
            "message_flag": "GET_SENT_SMS_LOCAL",
            "page_number": page,
            "data_per_page": str(data_per_page)
        }
        sent_messages = []
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                for m in r.json().get("message_list", []):
                    to_num = uni_decode(m.get("from", "")).lstrip(";")
                    text = uni_decode(m.get("subject", ""))
                    raw_time = m.get("received", "")
                    sent_messages.append({
                        "id": m.get("index"),
                        "sender": to_num,
                        "text": text,
                        "time": parse_modem_time_to_shamsi(raw_time),
                        "raw_time": raw_time,
                        "direction": "out",
                        "is_unread": False,
                        "is_missed_call": False
                    })
        except Exception as e:
            print(f"[ModemClient] get_sent_sms_list error: {e}")
        return sent_messages

    def get_conversations(self) -> Dict[str, Any]:
        """
        Combines incoming and outgoing SMS, matches with Phonebook contacts,
        and groups them into threaded conversations like a modern smartphone.
        """
        # 1. Contacts map
        contacts = self.get_phonebook()
        contacts_map = {}
        for c in contacts:
            norm = c.get("normalized_number")
            if norm and c.get("name"):
                contacts_map[norm] = c.get("name")

        # 2. Incoming messages
        inbox_data = self.get_sms_list(page=1, data_per_page=50)
        inbox_msgs = inbox_data.get("messages", [])
        for m in inbox_msgs:
            m["direction"] = "in"

        # 3. Sent messages
        sent_msgs = self.get_sent_sms_list(page=1, data_per_page=50)

        # 4. Group by normalized peer
        threads = {}
        for m in inbox_msgs:
            peer = normalize_phone(m.get("sender", ""))
            if not peer:
                peer = m.get("sender", "نامشخص")
            threads.setdefault(peer, []).append(m)

        for s in sent_msgs:
            peer = normalize_phone(s.get("sender", ""))
            if not peer:
                peer = s.get("sender", "نامشخص")
            threads.setdefault(peer, []).append(s)

        conversations = []
        total_unread = 0
        for peer, msgs in threads.items():
            # Sort messages chronologically (oldest to newest for chat view)
            msgs.sort(key=lambda x: x.get("raw_time", ""))
            unread_c = sum(1 for x in msgs if x.get("is_unread"))
            total_unread += unread_c
            last_msg = msgs[-1] if msgs else {}
            contact_name = contacts_map.get(peer, "")
            
            conversations.append({
                "peer_number": peer,
                "peer_name": contact_name,
                "display_name": contact_name if contact_name else peer,
                "last_message": last_msg.get("text", ""),
                "last_time": last_msg.get("time", ""),
                "raw_time": last_msg.get("raw_time", ""),
                "last_direction": last_msg.get("direction", "in"),
                "unread_count": unread_c,
                "messages": msgs
            })

        # Sort conversations by newest activity first
        conversations.sort(key=lambda x: x.get("raw_time", ""), reverse=True)

        return {
            "conversations": conversations,
            "total_conversations": len(conversations),
            "total_unread": total_unread,
            "contacts_count": len(contacts)
        }

    def reboot(self) -> bool:
        """Reboots modem."""
        url = f"{self.base_url}?method=get&module=duster&file=json_device_restart{int(time.time()*1000)}"
        try:
            r = requests.get(url, timeout=self.timeout)
            return r.status_code == 200
        except Exception:
            return False


if __name__ == "__main__":
    client = ModemClient()
    print("Testing get_conversations...")
    convs = client.get_conversations()
    print(f"Loaded {convs['total_conversations']} conversations.")

