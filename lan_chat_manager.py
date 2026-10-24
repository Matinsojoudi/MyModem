#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LAN Chat Room and WebRTC Voice/Video Calling Manager for Modem Dashboard.
Features:
- Instant LAN chat rooms with shareable links and QR codes
- No admin credentials required for guest room participants
- Device nickname / display name selection
- Real-time text messaging and file attachments on LAN (0 internet usage)
- Direct WebRTC peer-to-peer audio and video calls over Wi-Fi
- Multi-client signaling queue and presence heartbeat
"""

import os
import time
import json
import uuid
import threading
from typing import Dict, Any, List, Optional

ROOMS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shared_files", ".lan_rooms.json")
CHAT_UPLOADS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "shared_files", "chat_uploads")
os.makedirs(CHAT_UPLOADS_DIR, exist_ok=True)


def get_safe_chat_file_path(filename: str) -> tuple:
    """Return a sanitized safe filepath inside CHAT_UPLOADS_DIR."""
    base_name = os.path.basename(filename).strip()
    safe_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.- ()"
    clean_name = "".join(c for c in base_name if c in safe_chars or ord(c) > 127)
    if not clean_name or clean_name.startswith("."):
        clean_name = f"attachment_{int(time.time())}.dat"
    dest_path = os.path.join(CHAT_UPLOADS_DIR, clean_name)
    counter = 1
    name_root, ext = os.path.splitext(clean_name)
    while os.path.exists(dest_path):
        clean_name = f"{name_root}_{counter}{ext}"
        dest_path = os.path.join(CHAT_UPLOADS_DIR, clean_name)
        counter += 1
    return dest_path, clean_name


class LanChatManager:
    def __init__(self):
        self.lock = threading.Lock()
        self.rooms: Dict[str, Dict[str, Any]] = {}
        self._load_rooms()

    def _load_rooms(self):
        if os.path.exists(ROOMS_FILE):
            try:
                with open(ROOMS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for r_id, r in data.items():
                        r["participants"] = {}
                        r["signals"] = []
                        r["msg_seq"] = len(r.get("messages", []))
                        r["sig_seq"] = 0
                        # Ensure every existing message has a seq
                        for i, m in enumerate(r.get("messages", [])):
                            if "seq" not in m:
                                m["seq"] = i + 1
                    self.rooms = data
            except Exception:
                self.rooms = {}

    def _save_rooms(self):
        try:
            to_save = {}
            for r_id, r in self.rooms.items():
                to_save[r_id] = {
                    "id": r["id"],
                    "title": r["title"],
                    "created_at": r["created_at"],
                    "created_by": r.get("created_by", "admin"),
                    "messages": r["messages"][-200:],  # keep last 200 messages
                }
            with open(ROOMS_FILE, "w", encoding="utf-8") as f:
                json.dump(to_save, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def create_room(self, title: str, custom_id: Optional[str] = None) -> Dict[str, Any]:
        with self.lock:
            room_title = title.strip() or "اتاق گفتگوی شبکه محلی"
            if custom_id:
                clean_id = "".join(c for c in custom_id if c.isalnum() or c in "-_")[:30]
            else:
                clean_id = ""
            if not clean_id or clean_id in self.rooms:
                clean_id = f"room-{uuid.uuid4().hex[:6]}"

            first_msg = {
                "id": f"sys-{uuid.uuid4().hex[:6]}",
                "seq": 1,
                "sender_id": "system",
                "sender_name": "سامانه",
                "type": "system",
                "text": f"اتاق «{room_title}» ایجاد شد. برای شروع گفتگو و تماس، لینک یا بارکد این اتاق را با سایر افراد حاضر در شبکه به اشتراک بگذارید.",
                "time": time.strftime("%H:%M"),
                "timestamp": time.time(),
            }

            room = {
                "id": clean_id,
                "title": room_title,
                "created_at": time.time(),
                "created_by": "admin",
                "msg_seq": 1,
                "sig_seq": 0,
                "participants": {},  # client_id -> {id, name, joined_at, last_seen, color}
                "messages": [first_msg],
                "signals": [],  # list of {seq, from_id, to_id, type, data, timestamp}
            }
            self.rooms[clean_id] = room
            self._save_rooms()
            return room

    def delete_room(self, room_id: str) -> bool:
        with self.lock:
            if room_id in self.rooms:
                del self.rooms[room_id]
                self._save_rooms()
                return True
            return False

    def get_room(self, room_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            return self.rooms.get(room_id)

    def get_rooms_list(self, lan_url: str) -> List[Dict[str, Any]]:
        with self.lock:
            result = []
            now = time.time()
            for r_id, r in self.rooms.items():
                active_count = sum(1 for p in r["participants"].values() if now - p["last_seen"] < 35)
                formatted_time = time.strftime("%Y-%m-%d %H:%M", time.localtime(r["created_at"]))
                url = f"{lan_url}/room/{r_id}"
                result.append({
                    "id": r_id,
                    "room_id": r_id,
                    "title": r["title"],
                    "name": r["title"],
                    "created_at": r["created_at"],
                    "formatted_time": formatted_time,
                    "online_count": active_count,
                    "active_users": active_count,
                    "messages_count": len(r["messages"]),
                    "url": url,
                    "join_url": url,
                })
            result.sort(key=lambda x: x["created_at"], reverse=True)
            return result

    def join_room(self, room_id: str, name: str, client_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return None

            clean_name = name.strip() or "کاربر شبکه"
            now = time.time()

            colors = ["#38bdf8", "#34d399", "#fbbf24", "#f472b6", "#a78bfa", "#22d3ee", "#fb923c", "#4ade80"]

            # If client already exists and reconnected
            if client_id and client_id in room["participants"]:
                p = room["participants"][client_id]
                p["name"] = clean_name
                p["last_seen"] = now
                color = p["color"]
            else:
                client_id = f"client-{uuid.uuid4().hex[:8]}"
                color = colors[len(room["participants"]) % len(colors)]
                room["participants"][client_id] = {
                    "id": client_id,
                    "name": clean_name,
                    "joined_at": now,
                    "last_seen": now,
                    "color": color,
                }
                # Add system announcement
                room["msg_seq"] = room.get("msg_seq", 0) + 1
                sys_msg = {
                    "id": f"sys-{uuid.uuid4().hex[:6]}",
                    "seq": room["msg_seq"],
                    "sender_id": "system",
                    "sender_name": "سامانه",
                    "type": "system",
                    "text": f"«{clean_name}» وارد اتاق گفتگو شد.",
                    "time": time.strftime("%H:%M"),
                    "timestamp": now,
                }
                room["messages"].append(sys_msg)

            return {
                "ok": True,
                "client_id": client_id,
                "name": clean_name,
                "color": color,
                "room_title": room["title"],
                "room_id": room_id,
                "messages": room["messages"],
                "next_msg_seq": room.get("msg_seq", len(room["messages"])),
                "next_sig_seq": room.get("sig_seq", 0),
            }

    def leave_room(self, room_id: str, client_id: str):
        with self.lock:
            room = self.rooms.get(room_id)
            if not room or client_id not in room["participants"]:
                return
            p = room["participants"].pop(client_id, None)
            if p:
                room["msg_seq"] = room.get("msg_seq", 0) + 1
                room["messages"].append({
                    "id": f"sys-{uuid.uuid4().hex[:6]}",
                    "seq": room["msg_seq"],
                    "sender_id": "system",
                    "sender_name": "سامانه",
                    "type": "system",
                    "text": f"«{p['name']}» از اتاق گفتگو خارج شد.",
                    "time": time.strftime("%H:%M"),
                    "timestamp": time.time(),
                })

    def add_message(self, room_id: str, client_id: str, text: str, file_info: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return None

            sender = room["participants"].get(client_id)
            sender_name = sender["name"] if sender else "کاربر"
            sender_color = sender["color"] if sender else "#38bdf8"

            room["msg_seq"] = room.get("msg_seq", 0) + 1

            msg = {
                "id": f"msg-{uuid.uuid4().hex[:8]}",
                "seq": room["msg_seq"],
                "sender_id": client_id,
                "sender_name": sender_name,
                "sender_color": sender_color,
                "type": "file" if file_info else "text",
                "text": text.strip(),
                "file": file_info,
                "time": time.strftime("%H:%M"),
                "timestamp": time.time(),
            }
            room["messages"].append(msg)
            if len(room["messages"]) > 500:
                room["messages"] = room["messages"][-500:]
            self._save_rooms()
            return msg

    def add_signal(self, room_id: str, from_id: str, to_id: str, sig_type: str, data: Any) -> Optional[Dict[str, Any]]:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return None

            room["sig_seq"] = room.get("sig_seq", 0) + 1
            signal = {
                "seq": room["sig_seq"],
                "from_id": from_id,
                "to_id": to_id,
                "type": sig_type,
                "data": data,
                "timestamp": time.time(),
            }
            room["signals"].append(signal)

            # keep only signals within last 60 seconds
            cutoff = time.time() - 60
            room["signals"] = [s for s in room["signals"] if s["timestamp"] > cutoff]
            return signal

    def poll_events(self, room_id: str, client_id: str, last_msg_seq: int = 0, last_sig_seq: int = 0) -> Dict[str, Any]:
        with self.lock:
            room = self.rooms.get(room_id)
            if not room:
                return {"error": "Room not found", "closed": True}

            now = time.time()
            if client_id in room["participants"]:
                room["participants"][client_id]["last_seen"] = now

            # Prune inactive participants (35s timeout)
            for pid, pdata in list(room["participants"].items()):
                if pid != client_id and now - pdata["last_seen"] > 35:
                    del room["participants"][pid]
                    room["msg_seq"] = room.get("msg_seq", 0) + 1
                    room["messages"].append({
                        "id": f"sys-{uuid.uuid4().hex[:6]}",
                        "seq": room["msg_seq"],
                        "sender_id": "system",
                        "sender_name": "سامانه",
                        "type": "system",
                        "text": f"«{pdata['name']}» به علت قطع ارتباط از اتاق خارج شد.",
                        "time": time.strftime("%H:%M"),
                        "timestamp": now,
                    })

            # Fetch new messages where seq > last_msg_seq
            new_msgs = [m for m in room["messages"] if m.get("seq", 0) > last_msg_seq]
            current_max_msg_seq = room.get("msg_seq", len(room["messages"]))

            # Filter signals targeted to client_id or broadcast (to_id == "*")
            new_sigs = [
                s for s in room["signals"]
                if s.get("seq", 0) > last_sig_seq
                and s["from_id"] != client_id
                and (s["to_id"] == client_id or s["to_id"] == "*")
            ]
            current_max_sig_seq = room.get("sig_seq", 0)

            active_participants = [
                {
                    "id": p["id"],
                    "name": p["name"],
                    "color": p["color"],
                    "is_self": (p["id"] == client_id),
                }
                for p in room["participants"].values()
            ]

            return {
                "room_title": room["title"],
                "room_id": room_id,
                "messages": new_msgs,
                "next_msg_seq": current_max_msg_seq,
                "signals": new_sigs,
                "next_sig_seq": current_max_sig_seq,
                "participants": active_participants,
            }


lan_chat_manager = LanChatManager()
