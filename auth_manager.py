#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Authentication and Session Security Manager for Modem Dashboard.
Features:
- Salted PBKDF2-HMAC-SHA256 password hashing
- Cryptographically secure 256-bit session tokens
- Cookie-based authentication with 30-day persistence
- Brute-force protection with IP rate limiting
- Constant-time verification to prevent timing attacks
"""

import os
import json
import time
import hashlib
import secrets
from typing import Optional, Tuple, Dict, Any

AUTH_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "auth_config.json")
SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".sessions.json")

SESSION_DURATION = 30 * 86400  # 30 days
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_TIME = 300  # 5 minutes


def _hash_pw(password: str, salt_bytes: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt_bytes, 120000).hex()


class AuthManager:
    def __init__(self):
        self.failed_attempts: Dict[str, list] = {}  # ip -> list of timestamps
        self.sessions: Dict[str, float] = {}  # token -> expire_ts
        self._ensure_config()
        self._load_sessions()

    def _ensure_config(self):
        """Creates default credentials (admin / admin) if auth_config.json does not exist."""
        if not os.path.exists(AUTH_CONFIG_FILE):
            salt = secrets.token_bytes(16)
            hashed = _hash_pw("admin", salt)
            data = {
                "username": "admin",
                "salt": salt.hex(),
                "password_hash": hashed,
                "created_at": time.time(),
                "updated_at": time.time()
            }
            with open(AUTH_CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

    def _get_config(self) -> Dict[str, Any]:
        self._ensure_config()
        with open(AUTH_CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

    def _load_sessions(self):
        now = time.time()
        if os.path.exists(SESSIONS_FILE):
            try:
                with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    self.sessions = {t: exp for t, exp in raw.items() if exp > now}
            except Exception:
                self.sessions = {}

    def _save_sessions(self):
        now = time.time()
        self.sessions = {t: exp for t, exp in self.sessions.items() if exp > now}
        try:
            with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.sessions, f)
        except Exception:
            pass

    def is_ip_rate_limited(self, ip: str) -> bool:
        """Returns True if IP has exceeded failed login attempts in the lockout window."""
        now = time.time()
        attempts = [t for t in self.failed_attempts.get(ip, []) if now - t < LOCKOUT_TIME]
        self.failed_attempts[ip] = attempts
        return len(attempts) >= MAX_FAILED_ATTEMPTS

    def record_failed_attempt(self, ip: str):
        now = time.time()
        self.failed_attempts.setdefault(ip, []).append(now)

    def clear_failed_attempts(self, ip: str):
        if ip in self.failed_attempts:
            del self.failed_attempts[ip]

    def login(self, username: str, password: str, client_ip: str) -> Tuple[bool, Optional[str], str]:
        """
        Validates credentials and issues a secure 30-day session token.
        Returns (success, session_token, message).
        """
        if self.is_ip_rate_limited(client_ip):
            return False, None, "تعداد دفعات تلاش ناموفق بیش از حد مجاز است. لطفاً ۵ دقیقه دیگر تلاش کنید."

        cfg = self._get_config()
        stored_user = cfg.get("username", "admin")
        stored_salt = bytes.fromhex(cfg.get("salt", ""))
        stored_hash = cfg.get("password_hash", "")

        user_match = secrets.compare_digest(username.strip(), stored_user)
        pw_hash = _hash_pw(password, stored_salt)
        pw_match = secrets.compare_digest(pw_hash, stored_hash)

        if user_match and pw_match:
            self.clear_failed_attempts(client_ip)
            token = secrets.token_hex(32)
            self.sessions[token] = time.time() + SESSION_DURATION
            self._save_sessions()
            return True, token, "ورود با موفقیت انجام شد."
        else:
            self.record_failed_attempt(client_ip)
            return False, None, "نام کاربری یا رمز عبور اشتباه است."

    def validate_session(self, token: str) -> bool:
        """Checks if a session token is valid and unexpired."""
        if not token:
            return False
        exp = self.sessions.get(token)
        if exp and exp > time.time():
            return True
        return False

    is_valid_session = validate_session

    def logout(self, token: str):
        """Invalidates a session token."""
        if token in self.sessions:
            del self.sessions[token]
            self._save_sessions()

    revoke_session = logout

    def change_credentials(self, current_pass: str, new_user: str, new_pass: str) -> Tuple[bool, str]:
        """Updates admin username and/or password."""
        cfg = self._get_config()
        stored_salt = bytes.fromhex(cfg.get("salt", ""))
        stored_hash = cfg.get("password_hash", "")

        curr_hash = _hash_pw(current_pass, stored_salt)
        if not secrets.compare_digest(curr_hash, stored_hash):
            return False, "رمز عبور فعلی نادرست است."

        clean_user = new_user.strip() if new_user.strip() else cfg.get("username", "admin")
        if len(new_pass) < 4:
            return False, "رمز عبور جدید باید حداقل ۴ کاراکتر باشد."

        new_salt = secrets.token_bytes(16)
        new_hash = _hash_pw(new_pass, new_salt)

        cfg["username"] = clean_user
        cfg["salt"] = new_salt.hex()
        cfg["password_hash"] = new_hash
        cfg["updated_at"] = time.time()

        with open(AUTH_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

        return True, "اطلاعات ورود با موفقیت به‌روزرسانی شد."


auth_manager = AuthManager()
