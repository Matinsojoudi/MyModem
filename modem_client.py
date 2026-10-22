#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Core API Client for NWR-945X 4G Portable Wi-Fi Modem
Provides methods for:
- Modem status & battery telemetry
- SMS reading, decoding, sending, and deleting
- Missed call detection
- USSD code dialing
- Device reboot
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Any

MODEM_IP = "192.168.1.1"
BASE_URL = f"http://{MODEM_IP}/xml_action.cgi"


def uni_decode(hex_str: str) -> str:
    """Decodes UCS2 / UTF-16BE hex string from modem into Python string."""
    if not hex_str:
        return ""
    try:
        # Strip trailing odd characters if any
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
    # Modem standard time format
    return now.strftime("%y,%m,%d,%H,%M,%S,+3.5")


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

    def get_sms_list(self, page: int = 1, data_per_page: int = 20, box: str = "inbox") -> Dict[str, Any]:
        """
        Fetches and decodes SMS messages from modem.
        box: 'inbox' (received), 'outbox' (sent)
        """
        flag = "GET_RCV_SMS_LOCAL" if box == "inbox" else "GET_SENT_SMS_LOCAL"
        url = f"{self.base_url}?method=post&module=duster&file=json_message_set{int(time.time()*1000)}"
        payload = {
            "message_flag": flag,
            "page_number": page,
            "data_per_page": str(data_per_page)
        }
        
        result = {
            "messages": [],
            "page_number": page,
            "total_pages": 1,
            "total_messages": 0
        }
        
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                raw_list = data.get("message_list", [])
                result["total_pages"] = int(data.get("total_page_number", 1))
                result["total_messages"] = int(data.get("sms_nv_rev_long_num", len(raw_list)))
                
                decoded_messages = []
                for item in raw_list:
                    sender = uni_decode(item.get("from", "")).lstrip(";")
                    text = uni_decode(item.get("subject", ""))
                    recv_time = item.get("received", "")
                    status = item.get("status", "0")  # 1 = unread, 0 = read
                    msg_id = item.get("index", "")
                    
                    # Detect missed call SMS from operator
                    is_missed_call = False
                    caller_number = ""
                    if "تماس از دست رفته" in text or "تماس ازدست رفته" in text or "missed call" in text.lower():
                        is_missed_call = True
                        # Try extracting caller phone if present
                        for word in text.split():
                            clean_word = word.strip(".,;:\"'()[]{}")
                            if clean_word.startswith("+98") or (clean_word.startswith("09") and len(clean_word) >= 11):
                                caller_number = clean_word
                                break

                    decoded_messages.append({
                        "id": msg_id,
                        "sender": sender,
                        "text": text,
                        "time": recv_time,
                        "is_unread": status == "1",
                        "is_missed_call": is_missed_call,
                        "caller_number": caller_number
                    })
                
                result["messages"] = decoded_messages
        except Exception as e:
            print(f"[ModemClient] get_sms_list error: {e}")
            
        return result

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
                # Status result 3 means success
                return data.get("sms_cmd_status_result") == 3
        except Exception as e:
            print(f"[ModemClient] send_sms error: {e}")
        return False

    def delete_sms(self, index_ids: str) -> bool:
        """Deletes SMS by index id(s) (e.g. 'LRCV22,LRCV20,')."""
        if not index_ids.endswith(","):
            index_ids += ","
            
        url = f"{self.base_url}?method=post&module=duster&file=json_message_set{int(time.time()*1000)}"
        payload = {
            "message_flag": "DELETE_SMS",
            "sms_cmd": "6",
            "tags": "12",
            "mem_store": "1",
            "delete_message_id": index_ids
        }
        
        try:
            r = requests.post(url, json=payload, timeout=self.timeout)
            if r.status_code == 200:
                data = r.json()
                return data.get("sms_cmd_status_result") == 3
        except Exception as e:
            print(f"[ModemClient] delete_sms error: {e}")
        return False

    def send_ussd(self, code: str, timeout_sec: int = 10) -> str:
        """Sends a USSD command (e.g. '*100#') and polls for response string."""
        url_set = f"{self.base_url}?method=post&module=duster&file=json_ussd_set{int(time.time()*1000)}"
        payload = {
            "action": "1",
            "ussd_param": code
        }
        try:
            r = requests.post(url_set, json=payload, timeout=self.timeout)
            if r.status_code != 200:
                return "خطا در ارسال درخواست USSD"
        except Exception as e:
            return f"خطای ارتباط: {e}"

        # Poll ussd_info
        url_info = f"{self.base_url}?method=get&module=duster&file=json_ussd_info{int(time.time()*1000)}"
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            time.sleep(1.5)
            try:
                res = requests.get(url_info, timeout=self.timeout)
                if res.status_code == 200:
                    d = res.json()
                    ussd_type = d.get("ussd_type", "")
                    ussd_str = d.get("ussd_str", "")
                    if ussd_str:
                        return uni_decode(ussd_str)
                    if ussd_type in ("0", "1") and not ussd_str:
                        return "پاسخ خالی از اپراتور دریافت شد."
            except Exception:
                pass
                
        return "زمان انتظار برای پاسخ USSD به پایان رسید."

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
    status = client.get_status()
    print("Modem Status:", status.get("battery_percent", "?") if status else "Offline")
    sms_res = client.get_sms_list(page=1, data_per_page=3)
    print(f"Total SMS count: {sms_res['total_messages']}")
    for m in sms_res["messages"]:
        print(f"[{m['time']}] {m['sender']}: {m['text'][:50]}... (Missed Call: {m['is_missed_call']})")
