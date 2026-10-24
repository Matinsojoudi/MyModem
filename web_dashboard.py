#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Web Dashboard for Neterbit NWR-945X 4G Modem
Includes:
- Threaded smartphone-like 2-way SMS chat with inline composer
- Phonebook contacts management (SIM & Device) with one-click chat
- Bulk SMS Campaign with live character and SMS segment counter (70/67 Farsi, 160/153 English)
- USSD Dialing & Account portal
- Device Control & Telemetry
"""

import http.server
import socketserver
import json
import urllib.parse
import http.cookies
from modem_client import ModemClient
from auth_manager import auth_manager

PORT = 8080
client = ModemClient()

LOGIN_PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ورود امن به پنل مدیریت مودم</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-surface: rgba(22, 30, 49, 0.85);
            --border: rgba(255, 255, 255, 0.08);
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --danger: #f43f5e;
            --shadow: 0 20px 40px -15px rgba(0,0,0,0.5);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', system-ui, sans-serif; }
        body { background: var(--bg-base); color: var(--text-main); min-height: 100vh; display: flex; align-items: center; justify-content: center; padding: 20px; }
        .login-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 20px; padding: 36px 32px; width: 100%; max-width: 400px; box-shadow: var(--shadow); backdrop-filter: blur(16px); }
        .login-header { text-align: center; margin-bottom: 28px; }
        .login-icon { width: 56px; height: 56px; margin: 0 auto 16px; background: rgba(56, 189, 248, 0.12); border-radius: 16px; display: flex; align-items: center; justify-content: center; color: var(--accent); }
        .login-title { font-size: 19px; font-weight: 800; margin-bottom: 6px; }
        .login-sub { font-size: 13px; color: var(--text-muted); }
        .form-group { margin-bottom: 18px; }
        .form-label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--text-main); }
        .form-input { width: 100%; padding: 12px 14px; border-radius: 10px; border: 1px solid var(--border); background: rgba(15, 23, 42, 0.6); color: var(--text-main); font-size: 14px; outline: none; transition: border-color 0.2s; }
        .form-input:focus { border-color: var(--accent); }
        .btn-submit { width: 100%; padding: 12px; border-radius: 10px; border: none; background: var(--accent); color: #0b0f19; font-size: 14px; font-weight: 700; cursor: pointer; transition: opacity 0.2s; margin-top: 8px; display: flex; align-items: center; justify-content: center; gap: 8px; }
        .btn-submit:hover { opacity: 0.9; }
        .btn-submit:disabled { opacity: 0.6; cursor: not-allowed; }
        .login-error { background: rgba(244, 63, 94, 0.12); border: 1px solid rgba(244, 63, 94, 0.3); color: #fb7185; padding: 10px 14px; border-radius: 10px; font-size: 12px; font-weight: 600; margin-bottom: 18px; display: none; text-align: center; }
        .login-footer { margin-top: 24px; text-align: center; font-size: 11px; color: var(--text-muted); }
    </style>
</head>
<body>
    <div class="login-card">
        <div class="login-header">
            <div class="login-icon">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
            </div>
            <h1 class="login-title">ورود امن به پنل مودم</h1>
            <p class="login-sub">جهت دسترسی به پیامک‌ها، مخاطبین و مانیتورینگ وارد شوید</p>
        </div>
        <div id="login-error" class="login-error"></div>
        <form id="login-form" onsubmit="handleLoginSubmit(event)">
            <div class="form-group">
                <label class="form-label">نام کاربری:</label>
                <input type="text" id="username" class="form-input" placeholder="نام کاربری (پیش‌فرض: admin)" autocomplete="username" required autofocus>
            </div>
            <div class="form-group">
                <label class="form-label">رمز عبور:</label>
                <input type="password" id="password" class="form-input" placeholder="رمز عبور (پیش‌فرض: admin)" autocomplete="current-password" required>
            </div>
            <button type="submit" id="btn-login-submit" class="btn-submit">
                ورود به پنل
            </button>
        </form>
        <div class="login-footer">
            احراز هویت رمزنگاری‌شده و حفاظت در برابر نفوذ شبکه
        </div>
    </div>
    <script>
        async function handleLoginSubmit(e) {
            e.preventDefault();
            const btn = document.getElementById('btn-login-submit');
            const errDiv = document.getElementById('login-error');
            const user = document.getElementById('username').value.trim();
            const pass = document.getElementById('password').value;

            btn.disabled = true;
            btn.innerText = 'در حال بررسی...';
            errDiv.style.display = 'none';

            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ username: user, password: pass })
                });
                const data = await res.json();
                if (data.success) {
                    window.location.reload();
                } else {
                    errDiv.innerText = data.message || 'نام کاربری یا رمز عبور اشتباه است.';
                    errDiv.style.display = 'block';
                }
            } catch (err) {
                errDiv.innerText = 'خطا در ارتباط با سرور.';
                errDiv.style.display = 'block';
            } finally {
                btn.disabled = false;
                btn.innerText = 'ورود به پنل';
            }
        }
    </script>
</body>
</html>
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مدیریت پیام‌ها و مودم همراه</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-base: #0b0f19;
            --bg-surface: rgba(22, 30, 49, 0.75);
            --bg-card: rgba(30, 41, 67, 0.55);
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(56, 189, 248, 0.35);
            --text-main: #f1f5f9;
            --text-muted: #94a3b8;
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --bubble-in: rgba(30, 41, 67, 0.85);
            --bubble-out: linear-gradient(135deg, #0284c7, #2563eb);
            --success: #10b981;
            --danger: #f43f5e;
            --warning: #f59e0b;
            --input-bg: rgba(15, 23, 42, 0.6);
            --shadow-card: 0 10px 25px -5px rgba(0, 0, 0, 0.3);
        }
        body.light-theme {
            --bg-base: #f8fafc;
            --bg-surface: rgba(255, 255, 255, 0.85);
            --bg-card: rgba(241, 245, 249, 0.85);
            --border: rgba(0, 0, 0, 0.08);
            --border-hover: rgba(2, 132, 199, 0.35);
            --text-main: #0f172a;
            --text-muted: #64748b;
            --accent: #0284c7;
            --accent-glow: rgba(2, 132, 199, 0.2);
            --bubble-in: #e2e8f0;
            --bubble-out: linear-gradient(135deg, #0284c7, #2563eb);
            --input-bg: #ffffff;
            --shadow-card: 0 10px 25px -5px rgba(0, 0, 0, 0.06);
        }
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', system-ui, sans-serif; }
        body { background: var(--bg-base); color: var(--text-main); min-height: 100vh; padding: 20px; transition: background 0.3s; }
        .container { max-width: 1200px; margin: 0 auto; }
        .topbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }
        .brand { display: flex; align-items: center; gap: 10px; }
        .brand h1 { font-size: 18px; font-weight: 800; }
        .topbar-actions { display: flex; gap: 8px; }
        .btn-icon { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-main); padding: 8px 14px; border-radius: 10px; cursor: pointer; display: inline-flex; align-items: center; gap: 6px; font-size: 13px; font-weight: 600; }
        .btn-icon:hover { border-color: var(--accent); color: var(--accent); }
        .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 14px; margin-bottom: 20px; }
        .stat-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 14px; padding: 14px 18px; display: flex; align-items: center; justify-content: space-between; backdrop-filter: blur(12px); box-shadow: var(--shadow-card); }
        .stat-label { font-size: 12px; color: var(--text-muted); font-weight: 500; margin-bottom: 4px; }
        .stat-val { font-size: 20px; font-weight: 800; }
        .signal-bars { display: flex; align-items: flex-end; gap: 3px; height: 20px; }
        .signal-bar { width: 5px; background: rgba(255,255,255,0.15); border-radius: 2px; }
        body.light-theme .signal-bar { background: rgba(0,0,0,0.15); }
        .signal-bar:nth-child(1) { height: 25%; }
        .signal-bar:nth-child(2) { height: 42%; }
        .signal-bar:nth-child(3) { height: 60%; }
        .signal-bar:nth-child(4) { height: 80%; }
        .signal-bar:nth-child(5) { height: 100%; }
        .signal-bar.active { background: var(--success); }
        .signal-bar.weak { background: var(--danger); }
        .signal-bar.med { background: var(--warning); }
        .tabs { display: flex; gap: 8px; background: var(--bg-surface); padding: 6px; border-radius: 14px; border: 1px solid var(--border); margin-bottom: 20px; overflow-x: auto; }
        .tab-btn { flex: 1; padding: 10px 16px; border-radius: 10px; border: none; background: transparent; color: var(--text-muted); font-weight: 600; font-size: 14px; cursor: pointer; display: flex; align-items: center; justify-content: center; gap: 8px; white-space: nowrap; }
        .tab-btn.active { background: var(--accent); color: #0b0f19; font-weight: 700; box-shadow: 0 4px 12px var(--accent-glow); }
        .tab-content { display: none; background: var(--bg-surface); border: 1px solid var(--border); border-radius: 18px; padding: 22px; backdrop-filter: blur(16px); box-shadow: var(--shadow-card); min-height: 520px; }
        .tab-content.active { display: block; animation: fadeIn 0.2s ease; }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
        /* Chat Split Layout */
        .chat-layout { display: grid; grid-template-columns: 360px 1fr; gap: 16px; height: 600px; }
        @media (max-width: 860px) { .chat-layout { grid-template-columns: 1fr; height: auto; } }
        .conv-sidebar { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; display: flex; flex-direction: column; overflow: hidden; }
        .conv-header { padding: 12px; border-bottom: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }
        .conv-search { width: 100%; padding: 8px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--input-bg); color: var(--text-main); font-size: 13px; outline: none; }
        .conv-search:focus { border-color: var(--accent); }
        .conv-actions { display: flex; gap: 6px; justify-content: space-between; }
        .conv-list { flex: 1; overflow-y: auto; padding: 6px; display: flex; flex-direction: column; gap: 6px; }
        .conv-card { padding: 10px 12px; border-radius: 10px; border: 1px solid transparent; cursor: pointer; display: flex; align-items: center; gap: 10px; transition: background 0.15s; }
        .conv-card:hover { background: rgba(56, 189, 248, 0.08); border-color: var(--border-hover); }
        .conv-card.active { background: rgba(56, 189, 248, 0.15); border-color: var(--accent); }
        .avatar { width: 40px; height: 40px; border-radius: 50%; background: linear-gradient(135deg, #0284c7, #6366f1); color: #fff; display: flex; align-items: center; justify-content: center; font-weight: 700; font-size: 14px; flex-shrink: 0; }
        .conv-info { flex: 1; min-width: 0; }
        .conv-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 3px; }
        .conv-name { font-weight: 700; font-size: 13px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .conv-time { font-size: 11px; color: var(--text-muted); }
        .conv-bottom { display: flex; justify-content: space-between; align-items: center; }
        .conv-snippet { font-size: 12px; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 190px; }
        .badge-unread { background: var(--success); color: #fff; font-size: 10px; font-weight: 700; padding: 2px 7px; border-radius: 10px; }
        /* Active Chat Pane */
        .chat-main { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; display: flex; flex-direction: column; overflow: hidden; height: 100%; }
        .chat-header { padding: 12px 18px; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .chat-user-details { display: flex; align-items: center; gap: 10px; }
        .chat-user-title { font-weight: 700; font-size: 15px; }
        .chat-user-sub { font-size: 12px; color: var(--text-muted); }
        .chat-messages { flex: 1; overflow-y: auto; padding: 18px; display: flex; flex-direction: column; gap: 12px; }
        .chat-bubble { max-width: 75%; padding: 8px 12px; border-radius: 14px; font-size: 13px; line-height: 1.5; word-break: break-word; position: relative; }
        .bubble-text { white-space: pre-wrap; word-break: break-word; }
        .bubble-in { align-self: flex-start; background: var(--bubble-in); color: var(--text-main); border: 1px solid var(--border); border-bottom-right-radius: 3px; }
        .bubble-out { align-self: flex-end; background: var(--bubble-out); color: #ffffff; border-bottom-left-radius: 3px; box-shadow: 0 4px 12px rgba(2, 132, 199, 0.25); }
        .bubble-meta { font-size: 10px; margin-top: 4px; opacity: 0.8; text-align: left; }
        .bubble-in .bubble-meta { text-align: right; color: var(--text-muted); }
        .chat-composer { padding: 12px; border-top: 1px solid var(--border); display: flex; flex-direction: column; gap: 8px; }
        .composer-input-row { display: flex; gap: 8px; }
        .composer-input { flex: 1; padding: 10px 14px; border-radius: 10px; border: 1px solid var(--border); background: var(--input-bg); color: var(--text-main); font-size: 13px; outline: none; resize: none; min-height: 44px; max-height: 140px; line-height: 1.5; white-space: pre-wrap; }
        .composer-input:focus { border-color: var(--accent); }
        .btn-send { background: var(--accent); color: #0b0f19; font-weight: 700; border: none; border-radius: 10px; padding: 0 20px; cursor: pointer; display: flex; align-items: center; gap: 6px; font-size: 13px; }
        .btn-send:hover { opacity: 0.9; }
        .char-meter { display: flex; justify-content: space-between; font-size: 11px; color: var(--text-muted); padding: 0 4px; }
        /* Speed Stat Card */
        .speed-meters { display: flex; align-items: center; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
        .speed-pill { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 8px; font-size: 12px; font-weight: 700; }
        .speed-pill.speed-down { background: rgba(14, 165, 233, 0.12); color: #38bdf8; border: 1px solid rgba(14, 165, 233, 0.25); }
        .speed-pill.speed-up { background: rgba(168, 85, 247, 0.12); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.25); }
        body.light-theme .speed-pill.speed-down { background: #e0f2fe; color: #0284c7; border-color: #bae6fd; }
        body.light-theme .speed-pill.speed-up { background: #f3e8ff; color: #7e22ce; border-color: #e9d5ff; }
        .speed-dir { font-size: 13px; font-weight: 800; }
        .speed-icon-wrap { color: var(--accent); opacity: 0.9; }
        /* Bulk SMS Campaign */
        .bulk-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; }
        @media (max-width: 800px) { .bulk-grid { grid-template-columns: 1fr; } }
        .bulk-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 18px; }
        .bulk-title { font-weight: 700; font-size: 15px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; }
        .bulk-textarea { width: 100%; padding: 12px; border-radius: 10px; border: 1px solid var(--border); background: var(--input-bg); color: var(--text-main); font-size: 13px; outline: none; resize: vertical; min-height: 140px; }
        .bulk-textarea:focus { border-color: var(--accent); }
        .metric-badge-bar { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-top: 10px; }
        .metric-box { background: var(--input-bg); border: 1px solid var(--border); border-radius: 8px; padding: 8px; text-align: center; }
        .metric-num { font-weight: 800; font-size: 16px; color: var(--accent); }
        .metric-title { font-size: 10px; color: var(--text-muted); }
        .progress-bar-wrap { background: var(--input-bg); border: 1px solid var(--border); border-radius: 8px; height: 12px; overflow: hidden; margin: 12px 0; }
        .progress-bar-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #38bdf8, #10b981); transition: width 0.3s; }
        .bulk-table-wrap { max-height: 220px; overflow-y: auto; margin-top: 10px; border: 1px solid var(--border); border-radius: 8px; }
        table { width: 100%; border-collapse: collapse; font-size: 12px; }
        th, td { padding: 8px 12px; text-align: right; border-bottom: 1px solid var(--border); }
        th { background: rgba(0,0,0,0.1); color: var(--text-muted); font-weight: 600; }
        /* Contacts Grid */
        .contacts-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; gap: 10px; flex-wrap: wrap; }
        .contacts-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 14px; }
        .contact-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 14px; display: flex; align-items: center; gap: 12px; }
        .contact-card:hover { border-color: var(--border-hover); }
        .contact-actions { margin-right: auto; display: flex; gap: 6px; }
        .btn-sm { padding: 6px 10px; font-size: 11px; font-weight: 600; border-radius: 6px; border: none; cursor: pointer; display: inline-flex; align-items: center; gap: 4px; }
        .btn-primary { background: var(--accent); color: #0b0f19; }
        .btn-danger { background: rgba(244, 63, 94, 0.15); color: var(--danger); border: 1px solid rgba(244, 63, 94, 0.3); }
        .btn-secondary { background: rgba(255, 255, 255, 0.08); color: var(--text-main); border: 1px solid var(--border); }
        /* Modal */
        .modal-overlay { position: fixed; inset: 0; background: rgba(0, 0, 0, 0.65); backdrop-filter: blur(4px); display: none; align-items: center; justify-content: center; z-index: 999; }
        .modal-overlay.active { display: flex; }
        .modal-card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 16px; padding: 22px; width: 90%; max-width: 440px; box-shadow: var(--shadow-card); }
        .form-row { margin-bottom: 14px; }
        .form-row label { display: block; font-size: 12px; color: var(--text-muted); margin-bottom: 6px; font-weight: 600; }
        .form-row input, .form-row select { width: 100%; padding: 10px 12px; border-radius: 8px; border: 1px solid var(--border); background: var(--input-bg); color: var(--text-main); font-size: 13px; outline: none; }
        .form-row input:focus, .form-row select:focus { border-color: var(--accent); }
        /* Connected Devices */
        .devices-header-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; flex-wrap: wrap; gap: 12px; }
        .devices-filter-group { display: flex; gap: 6px; flex-wrap: wrap; }
        .btn-filter { padding: 6px 14px; border-radius: 8px; border: 1px solid var(--border); background: var(--input-bg); color: var(--text-muted); font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-filter.active, .btn-filter:hover { background: rgba(56, 189, 248, 0.15); color: var(--accent); border-color: rgba(56, 189, 248, 0.4); }
        .devices-summary-pills { display: flex; gap: 10px; margin-bottom: 18px; flex-wrap: wrap; }
        .dev-pill { background: var(--bg-card); border: 1px solid var(--border); border-radius: 10px; padding: 10px 16px; display: flex; align-items: center; gap: 10px; }
        .dev-pill-val { font-size: 18px; font-weight: 800; color: var(--text-main); }
        .dev-pill-label { font-size: 11px; color: var(--text-muted); }
        .devices-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
        .device-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 14px; padding: 16px; display: flex; flex-direction: column; justify-content: space-between; gap: 12px; transition: border-color 0.2s; position: relative; }
        .device-card.is-online { border-right: 4px solid var(--success); }
        .device-card.is-blocked { border-right: 4px solid var(--danger); }
        .device-card.is-offline { border-right: 4px solid var(--text-muted); opacity: 0.85; }
        .device-card.is-self { box-shadow: 0 0 0 1.5px var(--accent), 0 4px 18px rgba(56, 189, 248, 0.18); }
        .device-top { display: flex; justify-content: space-between; align-items: flex-start; gap: 8px; }
        .device-icon-box { width: 40px; height: 40px; border-radius: 10px; background: rgba(56, 189, 248, 0.1); color: var(--accent); display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
        .device-info { flex: 1; min-width: 0; }
        .device-name-row { display: flex; align-items: center; gap: 6px; margin-bottom: 4px; flex-wrap: wrap; }
        .device-name { font-weight: 700; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 170px; }
        .badge-self { background: rgba(245, 158, 11, 0.18); border: 1px solid rgba(245, 158, 11, 0.35); color: #fbbf24; font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 6px; }
        .device-badge-status { font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; }
        .badge-online { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
        .badge-blocked { background: rgba(244, 63, 94, 0.15); color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.3); }
        .badge-offline { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
        .device-meta-row { display: flex; justify-content: space-between; font-size: 12px; color: var(--text-muted); padding: 4px 0; border-bottom: 1px dashed var(--border); }
        .device-meta-val { font-weight: 600; color: var(--text-main); font-family: monospace; direction: ltr; }
        .traffic-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px; background: var(--input-bg); padding: 8px; border-radius: 8px; text-align: center; }
        .traffic-val { font-size: 12px; font-weight: 700; color: var(--text-main); }
        .traffic-lbl { font-size: 10px; color: var(--text-muted); }
        .device-actions { display: flex; gap: 8px; margin-top: 6px; flex-wrap: wrap; }
    </style>
</head>
<body>
    <div class="container">
        <!-- Topbar -->
        <div class="topbar">
            <div class="brand">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" style="color:var(--accent);"><rect x="2" y="2" width="20" height="8" rx="2"/><rect x="2" y="14" width="20" height="8" rx="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>
                <h1>مدیریت و مانیتورینگ مودم همراه</h1>
            </div>
            <div class="topbar-actions">
                <button class="btn-icon" onclick="toggleTheme()" id="theme-btn">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
                    تم روشن
                </button>
                <button class="btn-icon" onclick="openPasswordModal()" title="تنظیمات رمز عبور پنل">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0 1 10 0v4"/></svg>
                    امنیت پنل
                </button>
                <button class="btn-icon" onclick="handleLogout()" title="خروج از حساب مدیریت">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                    خروج
                </button>
                <button class="btn-icon" onclick="refreshStatus(); loadConversations();">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                    بروزرسانی
                </button>
            </div>
        </div>

        <!-- Telemetry Cards -->
        <div class="stats-grid">
            <div class="stat-card">
                <div>
                    <div class="stat-label">درصد باتری مودم</div>
                    <div class="stat-val" id="stat-battery">--%</div>
                </div>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--success);"><rect x="1" y="6" width="18" height="12" rx="2"/><line x1="23" y1="11" x2="23" y2="13"/></svg>
            </div>
            <div class="stat-card" onclick="switchTab('devices')" style="cursor:pointer;" title="مشاهده لیست و کنترل دستگاه‌های متصل">
                <div>
                    <div class="stat-label">دستگاه‌های متصل به وای‌فای</div>
                    <div class="stat-val" id="stat-wifi">--</div>
                </div>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent);"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>
            </div>
            <div class="stat-card">
                <div>
                    <div class="stat-label">سرعت زنده دانلود / آپلود</div>
                    <div class="speed-meters">
                        <div class="speed-pill speed-down" title="سرعت دانلود لحظه‌ای">
                            <span class="speed-dir">↓</span>
                            <span id="stat-speed-down" class="speed-val">۰ KB/s</span>
                        </div>
                        <div class="speed-pill speed-up" title="سرعت آپلود لحظه‌ای">
                            <span class="speed-dir">↑</span>
                            <span id="stat-speed-up" class="speed-val">۰ KB/s</span>
                        </div>
                    </div>
                </div>
                <div class="speed-icon-wrap" title="ترافیک لحظه‌ای شبکه">
                    <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M7 10v12M7 22l-4-4M7 22l4-4M17 14V2M17 2l-4 4M17 2l4 4"/>
                    </svg>
                </div>
            </div>
            <div class="stat-card">
                <div>
                    <div class="stat-label">آنتن‌دهی و سیگنال</div>
                    <div class="stat-val" id="stat-signal-text" style="font-size:14px; margin-bottom:4px;">--</div>
                    <div class="signal-bars">
                        <div class="signal-bar" id="bar1"></div>
                        <div class="signal-bar" id="bar2"></div>
                        <div class="signal-bar" id="bar3"></div>
                        <div class="signal-bar" id="bar4"></div>
                        <div class="signal-bar" id="bar5"></div>
                    </div>
                </div>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="color:var(--accent);"><path d="M2 20h.01"/><path d="M7 20v-4"/><path d="M12 20v-8"/><path d="M17 20V8"/><path d="M22 20V4"/></svg>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-btn active" id="tab-btn-chat" onclick="switchTab('chat')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                پیام‌ها و گفتگوها
            </button>
            <button class="tab-btn" id="tab-btn-bulk" onclick="switchTab('bulk')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
                ارسال پیامک انبوه
            </button>
            <button class="tab-btn" id="tab-btn-contacts" onclick="switchTab('contacts')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                مخاطبین مودم
            </button>
            <button class="tab-btn" id="tab-btn-devices" onclick="switchTab('devices')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>
                دستگاه‌های متصل
            </button>
            <button class="tab-btn" id="tab-btn-ussd" onclick="switchTab('ussd')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="4" y1="9" x2="20" y2="9"/><line x1="4" y1="15" x2="20" y2="15"/><line x1="10" y1="3" x2="8" y2="21"/><line x1="16" y1="3" x2="14" y2="21"/></svg>
                کدهای دستوری (USSD)
            </button>
            <button class="tab-btn" id="tab-btn-parental" onclick="switchTab('parental')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                محافظت از کودکان و امنیت
            </button>
            <button class="tab-btn" id="tab-btn-control" onclick="switchTab('control')">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
                کنترل مودم
            </button>
        </div>
        <!-- Tab 1: Chat & Conversations -->
        <div id="tab-chat" class="tab-content active">
            <div class="chat-layout">
                <!-- Sidebar: Conversations List -->
                <div class="conv-sidebar">
                    <div class="conv-header">
                        <input type="text" id="conv-search" class="conv-search" placeholder="جستجو در گفتگوها..." oninput="filterConversations()">
                        <div class="conv-actions">
                            <button class="btn-sm btn-primary" onclick="openNewChatModal()">
                                <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                                پیام جدید
                            </button>
                            <button class="btn-sm btn-secondary" id="btn-mark-all" onclick="markAllAsRead()">
                                خواندن همه
                            </button>
                            <button class="btn-sm btn-danger" onclick="deleteAllSMS()">
                                حذف همه
                            </button>
                        </div>
                    </div>
                    <div id="conv-list" class="conv-list">
                        <div style="padding:20px; text-align:center; color:var(--text-muted); font-size:12px;">در حال بارگذاری گفتگوها...</div>
                    </div>
                </div>

                <!-- Main: Active Chat Conversation -->
                <div class="chat-main" id="chat-main">
                    <div id="chat-empty-state" style="flex:1; display:flex; flex-direction:column; align-items:center; justify-content:center; color:var(--text-muted); padding:30px; text-align:center;">
                        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" style="opacity:0.4; margin-bottom:12px;"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
                        <div style="font-weight:700; font-size:15px; margin-bottom:6px;">هیچ گفتگویی انتخاب نشده است</div>
                        <div style="font-size:12px;">یک گفتگو را از لیست سمت راست انتخاب کنید یا روی «پیام جدید» کلیک کنید.</div>
                    </div>

                    <div id="chat-active-box" style="display:none; flex-direction:column; height:100%;">
                        <div class="chat-header">
                            <div class="chat-user-details">
                                <div class="avatar" id="active-chat-avatar">--</div>
                                <div>
                                    <div class="chat-user-title" id="active-chat-name">--</div>
                                    <div class="chat-user-sub" id="active-chat-sub">--</div>
                                </div>
                            </div>
                            <div style="display:flex; gap:6px;">
                                <button class="btn-sm btn-secondary" onclick="copyActiveNumber()">کپی شماره</button>
                                <button class="btn-sm btn-secondary" id="btn-save-contact" onclick="saveActiveAsContact()">ذخیره در مخاطبین</button>
                            </div>
                        </div>

                        <div class="chat-messages" id="chat-messages-scroll">
                            <!-- Messages bubbles will render here -->
                        </div>

                        <div class="chat-composer">
                            <div class="char-meter">
                                <span id="chat-counter-text">۰ کاراکتر | ۱ پیامک فارسی</span>
                                <span id="chat-status-msg" style="color:var(--text-muted);"></span>
                            </div>
                            <div class="composer-input-row">
                                <textarea id="chat-composer-input" class="composer-input" placeholder="متن پیامک خود را بنویسید... (ارسال با Enter، خط بعد با Shift+Enter)" rows="1" oninput="updateChatMetrics(); autoExpandTextarea(this);" onkeydown="handleChatKeyDown(event)"></textarea>
                                <button class="btn-send" id="btn-chat-send" onclick="sendChatMessage()">
                                    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                                    ارسال
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab 2: Bulk SMS Campaign -->
        <div id="tab-bulk" class="tab-content">
            <h3 style="font-size:16px; font-weight:800; margin-bottom:6px;">کمپین ارسال پیامک انبوه</h3>
            <p style="font-size:13px; color:var(--text-muted); margin-bottom:18px;">ارسال خودکار یک متن مشخص به لیستی از شماره‌های همراه با تاخیر استاندارد بین هر پیامک</p>

            <div class="bulk-grid">
                <!-- Left: Recipients & Message -->
                <div class="bulk-card">
                    <div class="bulk-title">
                        <span>لیست شماره‌های گیرنده</span>
                        <button class="btn-sm btn-secondary" onclick="openContactPickerModal()">انتخاب از مخاطبین</button>
                    </div>
                    <textarea id="bulk-numbers" class="bulk-textarea" placeholder="شماره‌ها را با کاما، خط جدید یا فاصله وارد کنید:&#10;09121111111&#10;09122222222&#10;09353333333" oninput="updateBulkNumbersCount()"></textarea>
                    <div style="font-size:12px; margin-top:8px; display:flex; justify-content:space-between;">
                        <span id="bulk-valid-count" style="font-weight:600; color:var(--accent);">۰ شماره معتبر</span>
                        <span style="color:var(--text-muted);">تکراری‌ها به طور خودکار حذف می‌شوند</span>
                    </div>

                    <div class="bulk-title" style="margin-top:20px;">
                        <span>متن پیامک ارسالی</span>
                    </div>
                    <textarea id="bulk-text" class="bulk-textarea" placeholder="متن پیامک را اینجا بنویسید..." oninput="updateBulkTextMetrics()"></textarea>

                    <!-- Realtime Character & SMS Segment Counter -->
                    <div class="metric-badge-bar">
                        <div class="metric-box">
                            <div class="metric-num" id="metric-chars">۰</div>
                            <div class="metric-title">کاراکترها</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-num" id="metric-segments">۰</div>
                            <div class="metric-title">بخش‌های پیامک</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-num" id="metric-remaining">۷۰</div>
                            <div class="metric-title">مانده تا پیامک بعد</div>
                        </div>
                        <div class="metric-box">
                            <div class="metric-num" id="metric-lang">فارسی</div>
                            <div class="metric-title">زبان متن</div>
                        </div>
                    </div>
                </div>

                <!-- Right: Campaign Controls & Live Progress -->
                <div class="bulk-card">
                    <div class="bulk-title">
                        <span>تنظیمات و پیشرفت ارسال</span>
                    </div>
                    <div class="form-row">
                        <label>فاصله زمانی بین هر ارسال (ثانیه):</label>
                        <select id="bulk-delay" style="padding:8px 12px; border-radius:8px; border:1px solid var(--border); background:var(--input-bg); color:var(--text-main); width:100%;">
                            <option value="1.5">۱.۵ ثانیه (سریع)</option>
                            <option value="2.5" selected>۲.۵ ثانیه (استاندارد و امن)</option>
                            <option value="4.0">۴ ثانیه (آرام و مطمئن)</option>
                        </select>
                    </div>

                    <div style="display:flex; gap:10px; margin-top:14px;">
                        <button class="btn-sm btn-primary" id="btn-start-bulk" style="flex:1; padding:10px; font-size:13px; justify-content:center;" onclick="startBulkCampaign()">
                            شروع ارسال انبوه
                        </button>
                        <button class="btn-sm btn-danger" id="btn-stop-bulk" style="padding:10px 16px; font-size:13px;" onclick="stopBulkCampaign()" disabled>
                            توقف ارسال
                        </button>
                    </div>

                    <div class="progress-bar-wrap">
                        <div class="progress-bar-fill" id="bulk-progress-bar"></div>
                    </div>

                    <div style="display:flex; justify-content:space-between; font-size:12px; font-weight:600; margin-bottom:12px;">
                        <span id="bulk-progress-text">۰٪ تکمیل شده</span>
                        <span id="bulk-stats-summary" style="color:var(--text-muted);">موفق: ۰ | ناموفق: ۰</span>
                    </div>

                    <div class="bulk-title" style="margin-top:10px; font-size:13px;">
                        <span>گزارش زنده ارسال به شماره‌ها</span>
                    </div>
                    <div class="bulk-table-wrap">
                        <table>
                            <thead>
                                <tr>
                                    <th>شماره تماس</th>
                                    <th>وضعیت</th>
                                    <th>زمان</th>
                                </tr>
                            </thead>
                            <tbody id="bulk-report-tbody">
                                <tr>
                                    <td colspan="3" style="text-align:center; color:var(--text-muted); padding:16px;">هنوز ارسالی شروع نشده است.</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab 3: Contacts Management -->
        <div id="tab-contacts" class="tab-content">
            <div class="contacts-toolbar">
                <div>
                    <h3 style="font-size:16px; font-weight:800; margin-bottom:4px;">دفترچه تلفن و مخاطبین مودم</h3>
                    <div style="font-size:13px; color:var(--text-muted);" id="contacts-count-text">در حال بارگذاری مخاطبین...</div>
                </div>
                <div style="display:flex; gap:8px;">
                    <input type="text" id="contacts-search" placeholder="جستجوی نام یا شماره..." style="padding:8px 12px; border-radius:8px; border:1px solid var(--border); background:var(--input-bg); color:var(--text-main); font-size:13px;" oninput="filterContactsList()">
                    <button class="btn-sm btn-primary" onclick="openAddContactModal()">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
                        مخاطب جدید
                    </button>
                </div>
            </div>
            <div id="contacts-grid" class="contacts-grid">
                <!-- Contact cards rendered here -->
            </div>
        </div>

        <!-- Tab: Connected Devices -->
        <div id="tab-devices" class="tab-content">
            <div class="devices-header-bar">
                <div>
                    <h3 style="font-size:16px; font-weight:800; margin-bottom:4px;">مدیریت و نظارت دستگاه‌های متصل به مودم</h3>
                    <div style="font-size:12px; color:var(--text-muted);">مشاهده حجم مصرف، سابقه اتصال، قطع موقت و مسدودسازی (بلاک)</div>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="btn-sm btn-secondary" onclick="resetDevicesTraffic()" title="صفر کردن کنتور دیتای دستگاه‌ها در مودم">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>
                        بازنشانی آمار مصرف
                    </button>
                    <button class="btn-sm btn-primary" onclick="loadDevices()">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                        بروزرسانی لیست
                    </button>
                </div>
            </div>

            <!-- Summary Counter Pills -->
            <div class="devices-summary-pills">
                <div class="dev-pill">
                    <div class="dev-pill-val" id="pill-online-count" style="color:var(--success);">0</div>
                    <div>
                        <div style="font-weight:700; font-size:13px;">دستگاه‌های آنلاین</div>
                        <div class="dev-pill-label">هم‌اکنون متصل به وای‌فای</div>
                    </div>
                </div>
                <div class="dev-pill">
                    <div class="dev-pill-val" id="pill-blocked-count" style="color:var(--danger);">0</div>
                    <div>
                        <div style="font-weight:700; font-size:13px;">دستگاه‌های مسدود</div>
                        <div class="dev-pill-label">دسترسی مسدود شده</div>
                    </div>
                </div>
                <div class="dev-pill">
                    <div class="dev-pill-val" id="pill-total-count" style="color:var(--accent);">0</div>
                    <div>
                        <div style="font-weight:700; font-size:13px;">کل سابقه اتصالات</div>
                        <div class="dev-pill-label">ذخیره در حافظه مودم</div>
                    </div>
                </div>
            </div>

            <!-- Filter & Search Toolbar -->
            <div class="contacts-toolbar">
                <div class="devices-filter-group">
                    <button class="btn-filter active" id="filter-all" onclick="setDeviceFilter('all')">همه دستگاه‌ها</button>
                    <button class="btn-filter" id="filter-online" onclick="setDeviceFilter('online')">فقط آنلاین</button>
                    <button class="btn-filter" id="filter-blocked" onclick="setDeviceFilter('blocked')">مسدود شده‌ها</button>
                    <button class="btn-filter" id="filter-offline" onclick="setDeviceFilter('offline')">سابقه / آفلاین</button>
                </div>
                <input type="text" id="device-search" class="conv-search" placeholder="جستجو با نام، IP یا MAC آدرس..." style="max-width:280px;" oninput="applyDeviceFilter()">
            </div>

            <!-- Devices Cards Grid -->
            <div id="devices-loading" style="text-align:center; padding:30px; color:var(--text-muted); font-size:13px;">
                در حال دریافت اطلاعات دستگاه‌ها از مودم...
            </div>
            <div id="devices-grid" class="devices-grid" style="display:none;"></div>
            <div id="devices-empty" style="display:none; text-align:center; padding:40px; color:var(--text-muted); font-size:13px;">
                دستگاهی با این مشخصات یافت نشد.
            </div>
        </div>

        <!-- Tab 4: USSD -->
        <div id="tab-ussd" class="tab-content">
            <h3 style="font-size:16px; font-weight:800; margin-bottom:8px;">استعلام بسته اینترنت و شارژ</h3>
            <div style="background:linear-gradient(135deg, rgba(235,107,34,0.15), rgba(255,152,0,0.08)); border:1px solid rgba(235,107,34,0.35); border-radius:12px; padding:16px; margin-bottom:20px; display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px;">
                <div>
                    <div style="font-weight:700; font-size:15px; color:#ff9800; margin-bottom:4px;">استعلام آنلاین از «شاتل موبایل من»</div>
                    <div style="font-size:13px; color:var(--text-muted);">مشاهده حجم باقیمانده، تاریخ انقضا و وضعیت شارژ بدون نیاز به USSD</div>
                </div>
                <a href="https://my.shatelmobile.ir" target="_blank" class="btn-sm btn-primary" style="background:#ff9800; color:#fff; text-decoration:none; padding:8px 16px;">ورود به پورتال شاتل موبایل</a>
            </div>

            <div style="border-top:1px solid var(--border); padding-top:16px;">
                <h4 style="font-size:14px; font-weight:700; margin-bottom:6px;">شماره‌گیری کدهای دستوری (USSD)</h4>
                <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:8px; padding:10px 14px; font-size:12px; color:var(--text-muted); margin-bottom:14px; line-height:1.6;">
                    <b>نکته فنی:</b> سیم‌کارت فعال مودم <b>شاتل موبایل</b> است و روی بستر 4G LTE کانال صوتی CSFB ندارد؛ بنابراین ممکن است دکل شبکه نشست USSD را روی مودم دیتا ببندد.
                </div>
                <div style="display:flex; gap:8px; margin-bottom:16px;">
                    <input type="text" id="ussd-code" placeholder="کد دستوری (مثلاً *1# یا *1*4#)" style="direction:ltr; padding:10px 14px; border-radius:8px; border:1px solid var(--border); background:var(--input-bg); color:var(--text-main); font-size:14px; flex:1;">
                    <button class="btn-sm btn-primary" style="padding:0 20px;" onclick="handleUSSD()">شماره‌گیری</button>
                </div>
                <label style="font-size:13px; color:var(--text-muted); font-weight:600;">نتیجه استعلام:</label>
                <div id="ussd-output" style="background:var(--input-bg); border:1px solid var(--border); border-radius:12px; padding:16px; min-height:80px; font-size:13px; line-height:1.7; white-space:pre-wrap; margin-top:8px;">برای مشاهده پاسخ، کد دستوری را وارد کرده و شماره‌گیری کنید.</div>
            </div>
        </div>

        <!-- Tab 5: Control -->
        <div id="tab-control" class="tab-content">
            <h3 style="font-size:16px; font-weight:800; margin-bottom:16px;">عملیات و مدیریت مودم</h3>
            <p style="color:var(--text-muted); font-size:14px; margin-bottom:20px;">از این بخش می‌توانید مودم را ری‌استارت کرده یا به پنل اصلی دسترسی داشته باشید.</p>
            <div style="display:flex; gap:12px;">
                <button class="btn-sm btn-danger" style="padding:10px 18px;" onclick="handleReboot()">ری‌استارت کردن مودم</button>
                <a href="http://192.168.1.1" target="_blank" class="btn-sm btn-primary" style="text-decoration:none; padding:10px 18px;">باز کردن پنل اصلی مودم</a>
            </div>
        </div>

        <!-- Tab 6: Parental & Child Protection -->
        <div id="tab-parental" class="tab-content">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; flex-wrap:wrap; gap:12px;">
                <div>
                    <h3 style="font-size:17px; font-weight:800; margin-bottom:6px;">محافظت از کودکان و امنیت خانواده</h3>
                    <p style="color:var(--text-muted); font-size:13px; margin:0;">اعمال فیلتر خودکار محتوای نامناسب، اجبار به جستجوی امن (SafeSearch) در گوگل و موتورهای جستجو، و نظارت بر شبکه</p>
                </div>
                <button class="btn-sm btn-secondary" onclick="loadParentalStatus()">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
                    بروزرسانی وضعیت
                </button>
            </div>

            <!-- Status Card -->
            <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:14px; padding:20px; margin-bottom:24px; display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:16px;">
                <div>
                    <div style="font-size:12px; color:var(--text-muted); margin-bottom:6px;">وضعیت فعال محافظت مودم:</div>
                    <div id="parental-status-badge" style="font-size:16px; font-weight:800; color:var(--primary); display:flex; align-items:center; gap:8px;">
                        در حال بارگذاری وضعیت...
                    </div>
                    <div id="parental-status-desc" style="font-size:12px; color:var(--text-muted); margin-top:6px;">
                        سرورهای DNS در حال حاضر: <span id="current-dns-display" style="direction:ltr; display:inline-block; font-family:monospace; font-weight:600;">-</span>
                    </div>
                </div>
                <div style="display:flex; gap:10px;">
                    <button class="btn-sm btn-danger" onclick="applyDnsProfile('off')" id="btn-disable-parental">
                        غیرفعال‌سازی فیلتر (حالت عادی)
                    </button>
                </div>
            </div>

            <!-- Protection Profiles Grid -->
            <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(300px, 1fr)); gap:18px; margin-bottom:28px;">
                
                <!-- Cloudflare Family Card -->
                <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:14px; padding:20px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                            <span style="font-weight:800; font-size:15px; color:var(--text-main);">محافظت از کودکان و جستجوی امن</span>
                            <span style="font-size:11px; background:rgba(16,185,129,0.15); color:var(--success); padding:3px 8px; border-radius:6px; font-weight:700;">پیشنهاد اصلی</span>
                        </div>
                        <p style="font-size:12.5px; color:var(--text-muted); line-height:1.7; margin-bottom:14px;">
                            با استفاده از سرورهای خانواده کلودفلر (1.1.1.3)، تمامی محتوای نامناسب و بدافزارها برای کل خانه مسدود شده و قابلیت <strong>SafeSearch اجباری</strong> روی گوگل، بینگ و یوتیوب قفل می‌شود تا کودک نتواند محتوای نامناسب را جستجو یا مشاهده کند.
                        </p>
                        <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:8px; padding:8px 12px; font-size:11.5px; color:var(--text-muted); margin-bottom:16px;">
                            دی‌ان‌اس اعمالی: <span style="direction:ltr; display:inline-block; font-family:monospace; font-weight:700; color:var(--text-main);">1.1.1.3 & 1.0.0.3</span>
                        </div>
                    </div>
                    <button class="btn-sm btn-primary" style="width:100%; justify-content:center; padding:10px;" onclick="applyDnsProfile('cloudflare_family')" id="btn-apply-cf">
                        فعال‌سازی محافظت کلودفلر
                    </button>
                </div>

                <!-- AdGuard Family Card -->
                <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:14px; padding:20px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                            <span style="font-weight:800; font-size:15px; color:var(--text-main);">محافظت خانواده و ضدتبلیغات</span>
                            <span style="font-size:11px; background:rgba(59,130,246,0.15); color:var(--primary); padding:3px 8px; border-radius:6px; font-weight:700;">ادگارد فمیلی</span>
                        </div>
                        <p style="font-size:12.5px; color:var(--text-muted); line-height:1.7; margin-bottom:14px;">
                            علاوه بر فیلتر کامل دامنه‌های نامناسب و قفل جستجوی امن در موتورهای جستجو، تمام تبلیغات پاپ‌آپ و اسپم‌های خطرناک را در وب‌سایت‌ها برای تبلت و گوشی کودک مسدود می‌کند.
                        </p>
                        <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:8px; padding:8px 12px; font-size:11.5px; color:var(--text-muted); margin-bottom:16px;">
                            دی‌ان‌اس اعمالی: <span style="direction:ltr; display:inline-block; font-family:monospace; font-weight:700; color:var(--text-main);">94.140.14.15 & 94.140.15.16</span>
                        </div>
                    </div>
                    <button class="btn-sm btn-primary" style="width:100%; justify-content:center; padding:10px;" onclick="applyDnsProfile('adguard_family')" id="btn-apply-adg">
                        فعال‌سازی محافظت ادگارد
                    </button>
                </div>

                <!-- Live DNS Logging & Monitoring (NextDNS) -->
                <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:14px; padding:20px; display:flex; flex-direction:column; justify-content:space-between;">
                    <div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                            <span style="font-weight:800; font-size:15px; color:var(--text-main);">نظارت و ثبت زنده دامنه‌ها (NextDNS)</span>
                            <span style="font-size:11px; background:rgba(245,158,11,0.15); color:var(--warning); padding:3px 8px; border-radius:6px; font-weight:700;">گزارش زنده</span>
                        </div>
                        <p style="font-size:12.5px; color:var(--text-muted); line-height:1.7; margin-bottom:14px;">
                            اگر می‌خواهید دقیقاً ببینید چه دامنه‌ها و سرویس‌هایی توسط دستگاه کودک صدا زده می‌شوند، آی‌پی DNS حساب اختصاصی خود در NextDNS را وارد کنید تا تمام لاگ‌ها در پنل شخصی‌تان نمایش داده شود.
                        </p>
                        <div style="display:flex; gap:8px; margin-bottom:14px;">
                            <input type="text" id="custom-dns1" placeholder="DNS اول (مثلاً 45.90.28.x)" style="direction:ltr; flex:1; padding:8px; border-radius:8px; border:1px solid var(--border); background:var(--input-bg); color:var(--text-main); font-size:12px;">
                            <input type="text" id="custom-dns2" placeholder="DNS دوم" style="direction:ltr; flex:1; padding:8px; border-radius:8px; border:1px solid var(--border); background:var(--input-bg); color:var(--text-main); font-size:12px;">
                        </div>
                    </div>
                    <div style="display:flex; gap:8px;">
                        <button class="btn-sm btn-primary" style="flex:1; justify-content:center; padding:10px;" onclick="saveCustomDns()">
                            اعمال DNS نظارتی
                        </button>
                        <a href="https://nextdns.io" target="_blank" class="btn-sm btn-secondary" style="text-decoration:none; padding:10px 14px;">
                            سایت NextDNS
                        </a>
                    </div>
                </div>
            </div>

            <!-- Quick Device Access & Sleep Control -->
            <div style="background:var(--bg-card); border:1px solid var(--border); border-radius:14px; padding:20px;">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:14px;">
                    <div>
                        <h4 style="font-size:15px; font-weight:800; margin-bottom:4px;">کنترل سریع اینترنت دستگاه کودک (ساعات خواب و مطالعه)</h4>
                        <p style="color:var(--text-muted); font-size:12.5px; margin:0;">می‌توانید در ساعات خواب شبانه یا زمان مطالعه، اینترنت دستگاه مشخص را با یک کلیک مسدود کنید.</p>
                    </div>
                    <button class="btn-sm btn-secondary" onclick="loadParentalDevices()">
                        بروزرسانی دستگاه‌ها
                    </button>
                </div>
                <div id="parental-devices-container" style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:12px; margin-top:14px;">
                    <!-- Rendered dynamically -->
                </div>
            </div>
        </div>
    </div>

    <!-- Modal: New Chat -->
    <div class="modal-overlay" id="modal-new-chat">
        <div class="modal-card">
            <h3 style="font-size:16px; font-weight:800; margin-bottom:14px;">شروع گفتگوی جدید</h3>
            <div class="form-row">
                <label>شماره تماس گیرنده:</label>
                <input type="text" id="new-chat-phone" placeholder="09xxxxxxxxx">
            </div>
            <div class="form-row">
                <label>متن اولین پیامک:</label>
                <textarea id="new-chat-text" style="width:100%; padding:10px; border-radius:8px; border:1px solid var(--border); background:var(--input-bg); color:var(--text-main); outline:none; resize:vertical; min-height:80px;" placeholder="متن پیامک..."></textarea>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:14px;">
                <button class="btn-sm btn-secondary" onclick="closeNewChatModal()">انصراف</button>
                <button class="btn-sm btn-primary" onclick="submitNewChat()">ارسال و شروع چت</button>
            </div>
        </div>
    </div>

    <!-- Modal: Add Contact -->
    <div class="modal-overlay" id="modal-add-contact">
        <div class="modal-card">
            <h3 style="font-size:16px; font-weight:800; margin-bottom:14px;">افزودن مخاطب به مودم</h3>
            <div class="form-row">
                <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                    <label style="margin-bottom:0;">نام و نام خانوادگی:</label>
                    <span id="add-contact-char-limit" style="font-size:11px; color:var(--text-muted);">حداکثر ۱۴ کاراکتر</span>
                </div>
                <input type="text" id="add-contact-name" placeholder="مثلاً: علی محمدی" oninput="updateAddContactLimit()">
            </div>
            <div class="form-row">
                <label>شماره موبایل:</label>
                <input type="text" id="add-contact-number" placeholder="09xxxxxxxxx" maxlength="25">
            </div>
            <div class="form-row">
                <label>دسته‌بندی:</label>
                <select id="add-contact-group">
                    <option value="common">عمومی</option>
                    <option value="family">خانواده</option>
                    <option value="friend">دوستان</option>
                    <option value="colleague">همکاران</option>
                </select>
            </div>
            <div class="form-row">
                <label>محل ذخیره‌سازی:</label>
                <select id="add-contact-loc" onchange="updateAddContactLimit()">
                    <option value="0">سیم‌کارت (SIM - حداکثر ۱۴ کاراکتر فارسی)</option>
                    <option value="1">حافظه مودم (Device - حداکثر ۳۰ کاراکتر)</option>
                </select>
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:14px;">
                <button class="btn-sm btn-secondary" onclick="closeAddContactModal()">انصراف</button>
                <button class="btn-sm btn-primary" onclick="submitAddContact()">ذخیره مخاطب</button>
            </div>
        </div>
    </div>

    <!-- Modal: Contact Picker for Bulk SMS -->
    <div class="modal-overlay" id="modal-contact-picker">
        <div class="modal-card" style="max-width:500px;">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
                <h3 style="font-size:16px; font-weight:800;">انتخاب شماره از مخاطبین</h3>
                <button class="btn-sm btn-secondary" onclick="toggleSelectAllContacts()">انتخاب همه</button>
            </div>
            <div id="contact-picker-list" style="max-height:280px; overflow-y:auto; display:flex; flex-direction:column; gap:8px; margin-bottom:14px; border:1px solid var(--border); border-radius:8px; padding:8px;">
                <!-- Checkboxes of contacts -->
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px;">
                <button class="btn-sm btn-secondary" onclick="closeContactPickerModal()">انصراف</button>
                <button class="btn-sm btn-primary" onclick="applyContactPickerSelection()">افزودن شماره‌های انتخابی</button>
            </div>
        </div>
    </div>

    <!-- Modal: Change Password & Security -->
    <div class="modal-overlay" id="modal-password">
        <div class="modal-card">
            <h3 style="font-size:16px; font-weight:800; margin-bottom:14px;">تنظیمات امنیت و رمز ورود پنل</h3>
            <div id="pwd-msg" style="display:none; padding:10px; border-radius:8px; font-size:12px; margin-bottom:12px; text-align:center;"></div>
            <div class="form-row">
                <label>رمز عبور فعلی:</label>
                <input type="password" id="pwd-current" placeholder="رمز عبور فعلی (پیش‌فرض: admin)" autocomplete="current-password">
            </div>
            <div class="form-row">
                <label>نام کاربری جدید (اختیاری):</label>
                <input type="text" id="pwd-new-user" placeholder="نام کاربری جدید (خالی = بدون تغییر)" autocomplete="username">
            </div>
            <div class="form-row">
                <label>رمز عبور جدید:</label>
                <input type="password" id="pwd-new" placeholder="رمز عبور جدید (حداقل ۴ کاراکتر)" autocomplete="new-password">
            </div>
            <div class="form-row">
                <label>تکرار رمز عبور جدید:</label>
                <input type="password" id="pwd-confirm" placeholder="تکرار رمز عبور جدید" autocomplete="new-password">
            </div>
            <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:16px;">
                <button class="btn-sm btn-secondary" onclick="closePasswordModal()">انصراف</button>
                <button class="btn-sm btn-primary" onclick="submitPasswordChange()">ذخیره و تغییر رمز</button>
            </div>
        </div>
    </div>

    <script>
        let allConversations = [];
        let activePeer = null;
        let allContacts = [];
        let isBulkRunning = false;
        let shouldStopBulk = false;

        // Theme Management
        function initTheme() {
            const saved = localStorage.getItem('modem_theme') || 'dark';
            if (saved === 'light') {
                document.body.classList.add('light-theme');
                document.getElementById('theme-btn').innerText = 'تم تاریک';
            } else {
                document.body.classList.remove('light-theme');
                document.getElementById('theme-btn').innerText = 'تم روشن';
            }
        }
        function toggleTheme() {
            const isLight = document.body.classList.toggle('light-theme');
            localStorage.setItem('modem_theme', isLight ? 'light' : 'dark');
            document.getElementById('theme-btn').innerText = isLight ? 'تم تاریک' : 'تم روشن';
        }

        // Tab Switching
        function switchTab(tabId) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            const btn = document.getElementById('tab-btn-' + tabId);
            if (btn) btn.classList.add('active');
            else if (window.event && window.event.currentTarget && window.event.currentTarget.classList.contains('tab-btn')) {
                window.event.currentTarget.classList.add('active');
            }
            const target = document.getElementById('tab-' + tabId);
            if (target) target.classList.add('active');
            if (tabId === 'chat') loadConversations();
            if (tabId === 'contacts') loadContacts();
            if (tabId === 'devices') loadDevices();
            if (tabId === 'parental') loadParentalStatus();
        }

        // Formatting & Security Utilities
        function formatNetworkSpeed(bytes) {
            const b = parseFloat(bytes) || 0;
            if (b < 1024) {
                return Math.round(b) + ' B/s';
            } else if (b < 1024 * 1024) {
                const kb = b / 1024;
                return (kb < 10 ? kb.toFixed(1) : Math.round(kb)) + ' KB/s';
            } else {
                const mb = b / (1024 * 1024);
                return mb.toFixed(2) + ' MB/s';
            }
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }

        function autoExpandTextarea(el) {
            el.style.height = 'auto';
            el.style.height = Math.min(el.scrollHeight, 140) + 'px';
        }

        let lastUnreadSmsCount = null;

        // Status Telemetry
        async function refreshStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (!data) return;
                document.getElementById('stat-battery').innerText = (data.battery_percent || '0') + '%';
                document.getElementById('stat-wifi').innerText = (data.wifi_clients_num || '0') + ' کلاینت';
                
                const downEl = document.getElementById('stat-speed-down');
                const upEl = document.getElementById('stat-speed-up');
                if (downEl) downEl.innerText = formatNetworkSpeed(data.rx_speed);
                if (upEl) upEl.innerText = formatNetworkSpeed(data.tx_speed);

                const sq = parseInt(data.signal_quality) || 0;
                const labels = { 0: 'بدون آنتن', 1: 'بسیار ضعیف', 2: 'ضعیف', 3: 'متوسط', 4: 'خوب', 5: 'عالی' };
                document.getElementById('stat-signal-text').innerText = labels[sq] || 'در دسترس';
                
                for (let i = 1; i <= 5; i++) {
                    const bar = document.getElementById('bar' + i);
                    if (!bar) continue;
                    bar.className = 'signal-bar';
                    if (i <= sq) {
                        if (sq <= 2) bar.classList.add('weak');
                        else if (sq === 3) bar.classList.add('med');
                        else bar.classList.add('active');
                    }
                }

                // Detect new incoming SMS and auto-refresh conversation list
                const currentUnread = parseInt(data.unread_long || data.new_sms_num || 0);
                if (lastUnreadSmsCount !== null && currentUnread !== lastUnreadSmsCount) {
                    loadConversations();
                }
                lastUnreadSmsCount = currentUnread;
            } catch (e) {
                console.error('Status fetch error:', e);
            }
        }

        // ================= CONVERSATIONS & CHAT =================
        async function loadConversations() {
            try {
                const res = await fetch('/api/conversations');
                const data = await res.json();
                allConversations = data.conversations || [];
                renderConversationList(allConversations);
                if (activePeer) {
                    const found = allConversations.find(c => c.peer_number === activePeer);
                    if (found) {
                        // If active conversation has unread incoming messages, mark them read
                        const unreadMsgs = (found.messages || []).filter(m => m.is_unread && m.direction === 'in');
                        if (unreadMsgs.length > 0) {
                            const unreadIds = unreadMsgs.map(m => m.id).filter(Boolean);
                            found.unread_count = 0;
                            found.messages.forEach(m => { m.is_unread = false; });
                            fetch('/api/mark_conversation_read', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({ ids: unreadIds })
                            }).catch(console.error);
                        }
                        renderActiveChat(found);
                    }
                }
            } catch (e) {
                console.error(e);
            }
        }

        function renderConversationList(list) {
            const container = document.getElementById('conv-list');
            if (!list || list.length === 0) {
                container.innerHTML = '<div style="padding:24px; text-align:center; color:var(--text-muted); font-size:12px;">گفتگویی یافت نشد.</div>';
                return;
            }
            let html = '';
            list.forEach(c => {
                const isActive = activePeer === c.peer_number;
                const initials = (c.peer_name ? c.peer_name.slice(0, 2) : c.peer_number.slice(-3)).toUpperCase();
                const prefix = c.last_direction === 'out' ? '<span style="color:var(--accent);">شما: </span>' : '';
                const unreadBadge = c.unread_count > 0 ? `<span class="badge-unread">${c.unread_count}</span>` : '';
                const cleanSnippet = escapeHtml((c.last_message || '').split('\\n').join(' ').split('\\r').join(''));
                html += `
                    <div class="conv-card ${isActive ? 'active' : ''}" onclick="selectConversation('${c.peer_number}')">
                        <div class="avatar">${initials}</div>
                        <div class="conv-info">
                            <div class="conv-top">
                                <span class="conv-name">${escapeHtml(c.display_name)}</span>
                                <span class="conv-time">${c.last_time || ''}</span>
                            </div>
                            <div class="conv-bottom">
                                <span class="conv-snippet">${prefix}${cleanSnippet}</span>
                                ${unreadBadge}
                            </div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        }

        function filterConversations() {
            const q = document.getElementById('conv-search').value.trim().toLowerCase();
            if (!q) {
                renderConversationList(allConversations);
                return;
            }
            const filtered = allConversations.filter(c => 
                c.display_name.toLowerCase().includes(q) || 
                c.peer_number.includes(q) || 
                (c.last_message && c.last_message.toLowerCase().includes(q))
            );
            renderConversationList(filtered);
        }

        function selectConversation(peerNumber) {
            activePeer = peerNumber;
            const conv = allConversations.find(c => c.peer_number === peerNumber);
            if (conv) {
                // Auto mark as read immediately when user views the chat
                const unreadMsgs = (conv.messages || []).filter(m => m.is_unread && m.direction === 'in');
                if (unreadMsgs.length > 0) {
                    const unreadIds = unreadMsgs.map(m => m.id).filter(Boolean);
                    conv.unread_count = 0;
                    conv.messages.forEach(m => { m.is_unread = false; });
                    fetch('/api/mark_conversation_read', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ ids: unreadIds })
                    }).catch(console.error);
                }
                renderConversationList(allConversations);
                renderActiveChat(conv);
            }
        }

        function renderActiveChat(conv) {
            document.getElementById('chat-empty-state').style.display = 'none';
            const box = document.getElementById('chat-active-box');
            box.style.display = 'flex';

            const initials = (conv.peer_name ? conv.peer_name.slice(0, 2) : conv.peer_number.slice(-3)).toUpperCase();
            document.getElementById('active-chat-avatar').innerText = initials;
            document.getElementById('active-chat-name').innerText = conv.display_name;
            document.getElementById('active-chat-sub').innerText = conv.peer_number;
            
            const btnSave = document.getElementById('btn-save-contact');
            if (btnSave) {
                btnSave.style.display = conv.peer_name ? 'none' : 'inline-block';
            }

            const messagesScroll = document.getElementById('chat-messages-scroll');
            let msgsHtml = '';
            (conv.messages || []).forEach(m => {
                const isOut = m.direction === 'out';
                const bubbleClass = isOut ? 'bubble-out' : 'bubble-in';
                const timeStr = m.time || '';
                const missedAlert = m.is_missed_call ? '<div style="font-weight:700; color:var(--danger); margin-bottom:4px;">تماس از دست رفته</div>' : '';
                const cleanText = escapeHtml((m.text || '').trim());
                msgsHtml += `<div class="chat-bubble ${bubbleClass}">${missedAlert}<div class="bubble-text">${cleanText}</div><div class="bubble-meta">${timeStr}</div></div>`;
            });
            messagesScroll.innerHTML = msgsHtml;
            messagesScroll.scrollTop = messagesScroll.scrollHeight;
            document.getElementById('chat-composer-input').focus();
        }

        function copyActiveNumber() {
            if (!activePeer) return;
            navigator.clipboard.writeText(activePeer);
            alert('شماره ' + activePeer + ' در کلیپ‌بورد کپی شد.');
        }

        function saveActiveAsContact() {
            if (!activePeer) return;
            document.getElementById('add-contact-number').value = activePeer;
            openAddContactModal();
        }

        async function sendChatMessage() {
            if (!activePeer) return;
            const input = document.getElementById('chat-composer-input');
            const text = input.value;
            if (!text.trim()) return;

            const btn = document.getElementById('btn-chat-send');
            const statusMsg = document.getElementById('chat-status-msg');
            btn.disabled = true;
            statusMsg.innerText = 'در حال ارسال پیامک...';

            try {
                const res = await fetch('/api/send_sms', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ phone: activePeer, text: text })
                });
                const data = await res.json();
                if (data.success) {
                    input.value = '';
                    input.style.height = 'auto';
                    updateChatMetrics();
                    statusMsg.innerText = 'ارسال شد';
                    setTimeout(() => { statusMsg.innerText = ''; }, 3000);
                    await loadConversations();
                } else {
                    alert('خطا در ارسال پیامک از طریق مودم.');
                    statusMsg.innerText = 'ارسال ناموفق';
                }
            } catch (e) {
                console.error(e);
                alert('خطای شبکه در ارتباط با مودم.');
            } finally {
                btn.disabled = false;
            }
        }

        function handleChatKeyDown(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendChatMessage();
            }
        }

        function updateChatMetrics() {
            const text = document.getElementById('chat-composer-input').value;
            const m = calculateSMSMetrics(text);
            const langName = m.isUnicode ? 'فارسی' : 'انگلیسی';
            document.getElementById('chat-counter-text').innerText = `${m.length} کاراکتر | ${m.segmentCount} پیامک ${langName}`;
        }

        // ================= BULK SMS CAMPAIGN =================
        function calculateSMSMetrics(text) {
            if (!text) {
                return { length: 0, isUnicode: false, segmentCount: 0, remainingInSegment: 70 };
            }
            let isUnicode = false;
            for (let i = 0; i < text.length; i++) {
                if (text.charCodeAt(i) > 127) {
                    isUnicode = true;
                    break;
                }
            }
            const length = text.length;
            let segmentCount = 1;
            let remainingInSegment = 0;

            if (isUnicode) {
                if (length <= 70) {
                    segmentCount = 1;
                    remainingInSegment = 70 - length;
                } else {
                    segmentCount = Math.ceil(length / 67);
                    remainingInSegment = (segmentCount * 67) - length;
                }
            } else {
                if (length <= 160) {
                    segmentCount = 1;
                    remainingInSegment = 160 - length;
                } else {
                    segmentCount = Math.ceil(length / 153);
                    remainingInSegment = (segmentCount * 153) - length;
                }
            }
            return { length, isUnicode, segmentCount, remainingInSegment };
        }

        function parseBulkNumbers(raw) {
            if (!raw) return [];
            const tokens = raw.split(/[\\r\\n,;\\s]+/);
            const valid = [];
            const seen = new Set();
            tokens.forEach(t => {
                let clean = t.replace(/[\\s\\-\\(\\)\\.\\+]/g, '');
                if (clean.startsWith('98') && clean.length >= 12) clean = '0' + clean.slice(2);
                if (clean.length === 10 && clean.startsWith('9')) clean = '0' + clean;
                if (/^09[0-9]{9}$/.test(clean) || /^[0-9]{3,8}$/.test(clean)) {
                    if (!seen.has(clean)) {
                        seen.add(clean);
                        valid.push(clean);
                    }
                }
            });
            return valid;
        }

        function updateBulkNumbersCount() {
            const raw = document.getElementById('bulk-numbers').value;
            const numbers = parseBulkNumbers(raw);
            document.getElementById('bulk-valid-count').innerText = `${numbers.length} شماره معتبر شناسایی شد`;
        }

        function updateBulkTextMetrics() {
            const text = document.getElementById('bulk-text').value;
            const m = calculateSMSMetrics(text);
            document.getElementById('metric-chars').innerText = m.length;
            document.getElementById('metric-segments').innerText = m.segmentCount;
            document.getElementById('metric-remaining').innerText = m.remainingInSegment;
            document.getElementById('metric-lang').innerText = m.isUnicode ? 'فارسی' : 'انگلیسی';
        }

        async function startBulkCampaign() {
            const numbers = parseBulkNumbers(document.getElementById('bulk-numbers').value);
            const text = document.getElementById('bulk-text').value.trim();
            const delaySec = parseFloat(document.getElementById('bulk-delay').value) || 2.0;

            if (numbers.length === 0) {
                alert('لطفاً حداقل یک شماره موبایل معتبر در کادر گیرندگان وارد کنید.');
                return;
            }
            if (!text) {
                alert('لطفاً متن پیامک را وارد کنید.');
                return;
            }
            if (!confirm(`آیا از شروع ارسال انبوه به ${numbers.length} شماره اطمینان دارید؟`)) {
                return;
            }

            isBulkRunning = true;
            shouldStopBulk = false;
            document.getElementById('btn-start-bulk').disabled = true;
            document.getElementById('btn-stop-bulk').disabled = false;

            const tbody = document.getElementById('bulk-report-tbody');
            tbody.innerHTML = numbers.map((n, i) => `
                <tr id="bulk-row-${i}">
                    <td>${n}</td>
                    <td><span id="bulk-badge-${i}" style="color:var(--text-muted);">در صف انتظار</span></td>
                    <td id="bulk-time-${i}">--</td>
                </tr>
            `).join('');

            let successCount = 0;
            let failCount = 0;
            const total = numbers.length;

            for (let i = 0; i < total; i++) {
                if (shouldStopBulk) {
                    alert('ارسال انبوه توسط کاربر متوقف شد.');
                    break;
                }
                const phone = numbers[i];
                const badge = document.getElementById('bulk-badge-' + i);
                const timeCell = document.getElementById('bulk-time-' + i);
                if (badge) {
                    badge.innerText = 'در حال ارسال...';
                    badge.style.color = 'var(--accent)';
                }

                try {
                    const res = await fetch('/api/send_sms', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({ phone, text })
                    });
                    const d = await res.json();
                    const nowStr = new Date().toLocaleTimeString('fa-IR');
                    if (timeCell) timeCell.innerText = nowStr;

                    if (d.success) {
                        successCount++;
                        if (badge) {
                            badge.innerText = 'ارسال موفق';
                            badge.style.color = 'var(--success)';
                        }
                    } else {
                        failCount++;
                        if (badge) {
                            badge.innerText = 'ناموفق';
                            badge.style.color = 'var(--danger)';
                        }
                    }
                } catch (e) {
                    failCount++;
                    if (badge) {
                        badge.innerText = 'خطای اتصال';
                        badge.style.color = 'var(--danger)';
                    }
                }

                // Update Progress
                const done = i + 1;
                const pct = Math.round((done / total) * 100);
                document.getElementById('bulk-progress-bar').style.width = pct + '%';
                document.getElementById('bulk-progress-text').innerText = `${pct}٪ (${done} از ${total})`;
                document.getElementById('bulk-stats-summary').innerText = `موفق: ${successCount} | ناموفق: ${failCount}`;

                if (i < total - 1) {
                    await new Promise(r => setTimeout(r, delaySec * 1000));
                }
            }

            isBulkRunning = false;
            document.getElementById('btn-start-bulk').disabled = false;
            document.getElementById('btn-stop-bulk').disabled = true;
            alert(`کمپین به پایان رسید.
ارسال موفق: ${successCount}
ناموفق: ${failCount}`);
            loadConversations();
        }

        function stopBulkCampaign() {
            if (isBulkRunning) {
                shouldStopBulk = true;
                document.getElementById('btn-stop-bulk').innerText = 'در حال توقف...';
            }
        }

        // ================= CONTACTS =================
        async function loadContacts() {
            try {
                const res = await fetch('/api/contacts');
                allContacts = await res.json();
                renderContactsGrid(allContacts);
                document.getElementById('contacts-count-text').innerText = `${allContacts.length} مخاطب در حافظه مودم`;
            } catch (e) {
                console.error(e);
            }
        }

        function renderContactsGrid(contacts) {
            const grid = document.getElementById('contacts-grid');
            if (!contacts || contacts.length === 0) {
                grid.innerHTML = '<div style="grid-column:1/-1; text-align:center; padding:30px; color:var(--text-muted);">مخاطبی در دفترچه تلفن مودم یافت نشد.</div>';
                return;
            }
            grid.innerHTML = contacts.map(c => {
                const hasName = c.name && c.name.trim() !== '' && c.name !== 'بی‌نام';
                const displayName = hasName ? c.name : c.number;
                const initials = displayName.slice(0, 2);
                const deleteId = (c.all_ids && c.all_ids.length > 0) ? c.all_ids.join(',') : c.id;
                return `
                <div class="contact-card">
                    <div class="avatar" style="background:linear-gradient(135deg, #6366f1, #0284c7);">${initials}</div>
                    <div>
                        <div style="font-weight:700; font-size:14px; margin-bottom:4px;">${displayName}</div>
                        <div style="font-size:11px; color:var(--accent);">${c.group} • ${c.storage}</div>
                    </div>
                    <div class="contact-actions">
                        <button class="btn-sm btn-primary" onclick="openChatWithContact('${c.normalized_number}')" title="شروع گفتگو">چت</button>
                        <button class="btn-sm btn-danger" onclick="deleteContact('${deleteId}')" title="حذف مخاطب">حذف</button>
                    </div>
                </div>
            `;}).join('');
        }

        function filterContactsList() {
            const q = document.getElementById('contacts-search').value.trim().toLowerCase();
            if (!q) {
                renderContactsGrid(allContacts);
                return;
            }
            const filtered = allContacts.filter(c => c.name.toLowerCase().includes(q) || c.number.includes(q));
            renderContactsGrid(filtered);
        }

        function openChatWithContact(phone) {
            document.querySelectorAll('.tab-btn')[0].click();
            selectConversation(phone);
        }

        async function deleteContact(id) {
            if (!confirm('آیا از حذف این مخاطب از مودم اطمینان دارید؟')) return;
            try {
                const res = await fetch('/api/contacts/delete', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ id })
                });
                const d = await res.json();
                if (d.success) {
                    loadContacts();
                } else {
                    alert('خطا در حذف مخاطب از مودم.');
                }
            } catch (e) {
                alert('خطا در برقراری ارتباط با مودم.');
            }
        }

        // Modals
        function openNewChatModal() { document.getElementById('modal-new-chat').classList.add('active'); }
        function closeNewChatModal() { document.getElementById('modal-new-chat').classList.remove('active'); }
        async function submitNewChat() {
            const phone = document.getElementById('new-chat-phone').value.trim();
            const text = document.getElementById('new-chat-text').value.trim();
            if (!phone || !text) {
                alert('شماره گیرنده و متن پیامک را وارد کنید.');
                return;
            }
            try {
                const res = await fetch('/api/send_sms', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ phone, text })
                });
                const d = await res.json();
                if (d.success) {
                    closeNewChatModal();
                    document.getElementById('new-chat-phone').value = '';
                    document.getElementById('new-chat-text').value = '';
                    await loadConversations();
                    selectConversation(phone);
                } else {
                    alert('خطا در ارسال پیامک.');
                }
            } catch (e) {
                alert('خطا در برقراری ارتباط با سرور.');
            }
        }

        function updateAddContactLimit() {
            const nameInput = document.getElementById('add-contact-name');
            const locSelect = document.getElementById('add-contact-loc');
            const limitLabel = document.getElementById('add-contact-char-limit');
            if (!nameInput || !locSelect || !limitLabel) return;
            const isSim = locSelect.value === '0';
            const val = nameInput.value || '';

            let isUnicode = false;
            for (let i = 0; i < val.length; i++) {
                if (val.charCodeAt(i) > 127) {
                    isUnicode = true;
                    break;
                }
            }

            const maxLen = isSim ? (isUnicode ? 14 : 20) : 30;
            nameInput.maxLength = maxLen;

            const storageName = isSim ? (isUnicode ? 'سیم‌کارت فارسی' : 'سیم‌کارت انگلیسی') : 'حافظه دستگاه';
            limitLabel.innerText = `${val.length} / ${maxLen} کاراکتر (${storageName})`;
            limitLabel.style.color = (maxLen - val.length <= 2) ? 'var(--danger)' : 'var(--text-muted)';
        }

        function openAddContactModal() {
            document.getElementById('modal-add-contact').classList.add('active');
            updateAddContactLimit();
        }
        function closeAddContactModal() { document.getElementById('modal-add-contact').classList.remove('active'); }
        async function submitAddContact() {
            const name = document.getElementById('add-contact-name').value.trim();
            const number = document.getElementById('add-contact-number').value.trim();
            const group = document.getElementById('add-contact-group').value;
            const location = document.getElementById('add-contact-loc').value;
            if (!name || !number) {
                alert('لطفاً نام و شماره تلفن را وارد کنید.');
                return;
            }

            let isUnicode = false;
            for (let i = 0; i < name.length; i++) {
                if (name.charCodeAt(i) > 127) {
                    isUnicode = true;
                    break;
                }
            }
            const maxLen = (location === '0') ? (isUnicode ? 14 : 20) : 30;
            if (name.length > maxLen) {
                alert(`نام مخاطب برای ذخیره در ${location === '0' ? 'سیم‌کارت' : 'حافظه دستگاه'} نمی‌تواند بیشتر از ${maxLen} کاراکتر باشد.`);
                return;
            }

            try {
                const res = await fetch('/api/contacts/add', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ name, number, group, location })
                });
                const d = await res.json();
                if (d.success) {
                    closeAddContactModal();
                    document.getElementById('add-contact-name').value = '';
                    document.getElementById('add-contact-number').value = '';
                    loadContacts();
                    loadConversations();
                } else {
                    alert('خطا در ذخیره مخاطب روی مودم.');
                }
            } catch (e) {
                alert('خطای ارتباط با سرور.');
            }
        }

        function openContactPickerModal() {
            const container = document.getElementById('contact-picker-list');
            if (allContacts.length === 0) {
                container.innerHTML = '<div style="padding:10px; color:var(--text-muted); text-align:center;">مخاطبی یافت نشد.</div>';
            } else {
                container.innerHTML = allContacts.map((c, idx) => `
                    <label style="display:flex; align-items:center; gap:8px; font-size:13px; cursor:pointer; padding:4px 6px;">
                        <input type="checkbox" class="contact-pick-chk" value="${c.normalized_number}">
                        <span style="font-weight:600;">${c.name}</span>
                        <span style="color:var(--text-muted); direction:ltr;">(${c.number})</span>
                    </label>
                `).join('');
            }
            document.getElementById('modal-contact-picker').classList.add('active');
        }
        function closeContactPickerModal() { document.getElementById('modal-contact-picker').classList.remove('active'); }
        function toggleSelectAllContacts() {
            const boxes = document.querySelectorAll('.contact-pick-chk');
            const allChecked = Array.from(boxes).every(b => b.checked);
            boxes.forEach(b => b.checked = !allChecked);
        }
        function applyContactPickerSelection() {
            const selected = [];
            document.querySelectorAll('.contact-pick-chk:checked').forEach(b => selected.push(b.value));
            if (selected.length > 0) {
                const textarea = document.getElementById('bulk-numbers');
                const existing = parseBulkNumbers(textarea.value);
                const merged = Array.from(new Set([...existing, ...selected]));
                textarea.value = merged.join('\\n');
                updateBulkNumbersCount();
            }
            closeContactPickerModal();
        }

        // Global Operations
        async function markAllAsRead() {
            const btn = document.getElementById('btn-mark-all');
            if (btn) { btn.disabled = true; btn.innerText = 'در حال ثبت...'; }
            try {
                await fetch('/api/mark_all_read', { method: 'POST' });
                await loadConversations();
                await refreshStatus();
            } catch (e) {
                alert('خطا در خواندن همه پیام‌ها');
            } finally {
                if (btn) { btn.disabled = false; btn.innerText = 'خواندن همه'; }
            }
        }

        async function deleteAllSMS() {
            if (!confirm('آیا از حذف تمام پیامک‌های مودم مطمئن هستید؟')) return;
            try {
                await fetch('/api/delete_all_sms', { method: 'POST' });
                activePeer = null;
                document.getElementById('chat-empty-state').style.display = 'flex';
                document.getElementById('chat-active-box').style.display = 'none';
                await loadConversations();
                await refreshStatus();
            } catch (e) {
                alert('خطا در حذف پیام‌ها');
            }
        }

        async function handleUSSD() {
            const code = document.getElementById('ussd-code').value.trim();
            const output = document.getElementById('ussd-output');
            if (!code) return;
            output.style.color = 'var(--text-muted)';
            output.textContent = 'در حال ارسال کد به شبکه...';
            try {
                const res = await fetch('/api/ussd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ code })
                });
                const d = await res.json();
                const safe = (d.result || 'پاسخی دریافت نشد.')
                    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                    .replace(/(https?:\\/\\/[^\\s]+)/g, '<a href="$1" target="_blank" style="color:var(--accent); text-decoration:underline;">$1</a>');
                output.style.color = (d.result || '').includes('بسته شد') ? 'var(--warning)' : 'var(--text-main)';
                output.innerHTML = safe;
            } catch (e) {
                output.style.color = 'var(--danger)';
                output.textContent = 'خطا در ارتباط با مودم.';
            }
        }

        async function handleReboot() {
            if (!confirm('آیا مطمئن هستید که می‌خواهید مودم را ری‌استارت کنید؟')) return;
            await fetch('/api/reboot', { method: 'POST' });
            alert('دستور ری‌استارت ارسال شد.');
        }

        // ================= CONNECTED DEVICES MANAGEMENT =================
        let currentDevices = [];
        let currentDeviceFilter = 'all';
        let currentClientIp = '';

        async function loadDevices() {
            const loading = document.getElementById('devices-loading');
            const grid = document.getElementById('devices-grid');
            const empty = document.getElementById('devices-empty');
            
            try {
                const res = await fetch('/api/devices');
                if (res.status === 401) {
                    window.location.reload();
                    return;
                }
                const data = await res.json();
                currentDevices = data.devices || [];
                currentClientIp = data.current_client_ip || '';

                // Update summary pills
                const onlineCount = data.online_count !== undefined ? data.online_count : currentDevices.filter(d => d.status === 'online').length;
                const blockedCount = data.blocked_count !== undefined ? data.blocked_count : currentDevices.filter(d => d.status === 'blocked').length;
                const totalCount = data.total_count !== undefined ? data.total_count : currentDevices.length;

                document.getElementById('pill-online-count').innerText = onlineCount;
                document.getElementById('pill-blocked-count').innerText = blockedCount;
                document.getElementById('pill-total-count').innerText = totalCount;
                
                const statWifi = document.getElementById('stat-wifi');
                if (statWifi) statWifi.innerText = onlineCount + ' کلاینت';

                applyDeviceFilter();
            } catch (err) {
                console.error('Error fetching devices:', err);
                if (loading) loading.innerText = 'خطا در بارگذاری اطلاعات دستگاه‌ها از مودم.';
            }
        }

        function setDeviceFilter(filter) {
            currentDeviceFilter = filter;
            document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
            const activeBtn = document.getElementById('filter-' + filter);
            if (activeBtn) activeBtn.classList.add('active');
            applyDeviceFilter();
        }

        function applyDeviceFilter() {
            const query = (document.getElementById('device-search')?.value || '').toLowerCase().trim();
            const filtered = currentDevices.filter(d => {
                const matchesFilter = (currentDeviceFilter === 'all') || (d.status === currentDeviceFilter);
                if (!matchesFilter) return false;
                if (!query) return true;
                const name = (d.name || '').toLowerCase();
                const ip = (d.ip || '').toLowerCase();
                const mac = (d.mac || '').toLowerCase();
                return name.includes(query) || ip.includes(query) || mac.includes(query);
            });

            renderDevicesGrid(filtered);
        }

        function renderDevicesGrid(list) {
            const loading = document.getElementById('devices-loading');
            const grid = document.getElementById('devices-grid');
            const empty = document.getElementById('devices-empty');
            if (loading) loading.style.display = 'none';

            if (!list || list.length === 0) {
                if (grid) grid.style.display = 'none';
                if (empty) empty.style.display = 'block';
                return;
            }

            if (empty) empty.style.display = 'none';
            if (grid) grid.style.display = 'grid';

            let html = '';
            list.forEach(d => {
                const isOnline = d.status === 'online' || d.is_online === true;
                const isBlocked = d.status === 'blocked' || d.is_blocked === true;
                const isOffline = !isOnline && !isBlocked;

                // Accurately detect if this card belongs to the user accessing the dashboard
                const isSelf = Boolean(
                    (d.is_host && (currentClientIp === '127.0.0.1' || currentClientIp === d.ip)) ||
                    (d.ip && d.ip !== 'آفلاین' && d.ip !== 'NA' && d.ip === currentClientIp)
                );

                let cardClass = isOnline ? 'is-online' : (isBlocked ? 'is-blocked' : 'is-offline');
                if (isSelf) cardClass += ' is-self';

                const badgeClass = isOnline ? 'badge-online' : (isBlocked ? 'badge-blocked' : 'badge-offline');
                const badgeText = isOnline ? 'آنلاین' : (isBlocked ? 'مسدود شده' : 'سابقه (آفلاین)');

                const nameLower = (d.name || '').toLowerCase();
                let iconSvg = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M5 12.55a11 11 0 0 1 14.08 0"/><path d="M1.42 9a16 16 0 0 1 21.16 0"/><path d="M8.53 16.11a6 6 0 0 1 6.95 0"/><line x1="12" y1="20" x2="12.01" y2="20"/></svg>';
                if (nameLower.includes('macbook') || nameLower.includes('pc') || nameLower.includes('laptop') || nameLower.includes('desktop')) {
                    iconSvg = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="12" rx="2"/><line x1="2" y1="20" x2="22" y2="20"/></svg>';
                } else if (nameLower.includes('phone') || nameLower.includes('iphone') || nameLower.includes('android') || nameLower.includes('galaxy') || nameLower.includes('redmi') || nameLower.includes('xiaomi')) {
                    iconSvg = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="5" y="2" width="14" height="20" rx="2" ry="2"/><line x1="12" y1="18" x2="12.01" y2="18"/></svg>';
                }

                const displayName = escapeHtml(d.name || 'دستگاه بدون نام');
                const selfBadge = isSelf ? '<span class="badge-self">این دستگاه (شما)</span>' : '';

                let actionBtns = '';
                const safeMac = escapeHtml(d.mac);
                const safeName = escapeHtml(d.name || d.mac).replace(/'/g, "\\'");

                if (isBlocked) {
                    actionBtns = `
                        <button class="btn-sm btn-primary" onclick="unblockDevice('${safeMac}', '${safeName}')">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>
                            رفع مسدودی (آنبلاک)
                        </button>
                    `;
                } else if (isOnline) {
                    actionBtns = `
                        <button class="btn-sm btn-danger" onclick="blockDevice('${safeMac}', '${safeName}', ${isSelf})">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                            مسدود کردن (بلاک)
                        </button>
                        <button class="btn-sm btn-secondary" onclick="disconnectDevice('${safeMac}', '${safeName}')">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"/><line x1="12" y1="2" x2="12" y2="12"/></svg>
                            قطع اتصال
                        </button>
                    `;
                } else {
                    actionBtns = `
                        <button class="btn-sm btn-danger" onclick="blockDevice('${safeMac}', '${safeName}', false)">
                            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg>
                            مسدودسازی پیشگیرانه
                        </button>
                    `;
                }

                html += `
                    <div class="device-card ${cardClass}">
                        <div>
                            <div class="device-top">
                                <div class="device-icon-box">${iconSvg}</div>
                                <div class="device-info">
                                    <div class="device-name-row">
                                        <span class="device-name" title="${displayName}">${displayName}</span>
                                        ${selfBadge}
                                    </div>
                                    <span class="device-badge-status ${badgeClass}">${badgeText}</span>
                                </div>
                            </div>
                            
                            <div style="margin-top:12px;">
                                <div class="device-meta-row">
                                    <span>آدرس IP:</span>
                                    <span class="device-meta-val" onclick="copyText('${d.ip}', 'IP')" style="cursor:pointer;" title="کلیک برای کپی">${escapeHtml(d.ip || '--')}</span>
                                </div>
                                <div class="device-meta-row">
                                    <span>آدرس MAC:</span>
                                    <span class="device-meta-val" onclick="copyText('${d.mac}', 'MAC')" style="cursor:pointer;" title="کلیک برای کپی">${escapeHtml(d.mac || '--')}</span>
                                </div>
                                <div class="device-meta-row">
                                    <span>مدت زمان اتصال:</span>
                                    <span style="font-weight:600; color:var(--text-main); font-size:12px;">${escapeHtml(d.duration_str || 'نامشخص')}</span>
                                </div>
                            </div>

                            <div style="margin-top:10px;">
                                <div class="traffic-grid">
                                    <div>
                                        <div class="traffic-val" style="color:#38bdf8;">${escapeHtml(d.rx_str || '0 B')}</div>
                                        <div class="traffic-lbl">دانلود</div>
                                    </div>
                                    <div>
                                        <div class="traffic-val" style="color:#c084fc;">${escapeHtml(d.tx_str || '0 B')}</div>
                                        <div class="traffic-lbl">آپلود</div>
                                    </div>
                                    <div>
                                        <div class="traffic-val" style="color:#10b981;">${escapeHtml(d.total_str || '0 B')}</div>
                                        <div class="traffic-lbl">مجموع مصرف</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="device-actions">
                            ${actionBtns}
                        </div>
                    </div>
                `;
            });

            grid.innerHTML = html;
        }

        async function blockDevice(mac, name, isSelf) {
            if (!mac) return;
            if (isSelf) {
                const confirmed = confirm(
                    'هشدار امنیتی بسیار مهم:\\n' +
                    'این دستگاه (' + (name || mac) + ') همان کامپیوتر یا موبایلی است که هم‌اکنون با آن وارد پنل مدیریت شده‌اید!\\n\\n' +
                    'در صورت مسدودسازی (بلاک)، بلافاصله ارتباط وای‌فای شما با مودم قطع خواهد شد و دسترسی‌تان قطع می‌شود.\\n\\n' +
                    'آیا واقعاً و با اطمینان کامل می‌خواهید این دستگاه را بلاک کنید؟'
                );
                if (!confirmed) return;
            } else {
                if (!confirm('آیا از مسدود کردن دستگاه «' + (name || mac) + '» و قطع دسترسی آن مطمئن هستید؟')) return;
            }

            try {
                const res = await fetch('/api/devices/block', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ mac })
                });
                const data = await res.json();
                if (data.success) {
                    alert('دستگاه با موفقیت مسدود شد.');
                    loadDevices();
                } else {
                    alert('خطا در اعمال دستور به مودم.');
                }
            } catch (err) {
                alert('خطا در ارتباط با سرور.');
            }
        }

        async function unblockDevice(mac, name) {
            if (!mac) return;
            if (!confirm('آیا مایل به رفع مسدودی (آنبلاک) دستگاه «' + (name || mac) + '» هستید؟')) return;

            try {
                const res = await fetch('/api/devices/unblock', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ mac })
                });
                const data = await res.json();
                if (data.success) {
                    alert('مسدودی دستگاه با موفقیت برطرف شد.');
                    loadDevices();
                } else {
                    alert('خطا در اعمال دستور به مودم.');
                }
            } catch (err) {
                alert('خطا در ارتباط با سرور.');
            }
        }

        async function disconnectDevice(mac, name) {
            if (!mac) return;
            if (!confirm('آیا از قطع موقت اتصال دستگاه «' + (name || mac) + '» مطمئن هستید؟ (دستگاه می‌تواند مجدداً متصل شود)')) return;

            try {
                const res = await fetch('/api/devices/disconnect', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ mac })
                });
                const data = await res.json();
                if (data.success) {
                    alert('دستور قطع اتصال به مودم ارسال شد.');
                    loadDevices();
                } else {
                    alert('خطا در اعمال دستور به مودم.');
                }
            } catch (err) {
                alert('خطا در ارتباط با سرور.');
            }
        }

        async function resetDevicesTraffic() {
            if (!confirm('آیا از بازنشانی و صفر کردن آمار مصرف دیتای دستگاه‌ها در مودم مطمئن هستید؟')) return;

            try {
                const res = await fetch('/api/devices/reset_traffic', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({})
                });
                const data = await res.json();
                if (data.success) {
                    alert('آمار مصرف دستگاه‌ها با موفقیت ریست شد.');
                    loadDevices();
                } else {
                    alert('خطا در ریست آمار.');
                }
            } catch (err) {
                alert('خطا در برقراری ارتباط.');
            }
        }

        function copyText(val, label) {
            if (!val) return;
            navigator.clipboard.writeText(val);
            alert(label + ' (' + val + ') در کلیپ‌بورد کپی شد.');
        }

        // ================= PARENTAL CONTROL & FAMILY DNS =================
        async function loadParentalStatus() {
            try {
                const res = await fetch('/api/dns');
                if (res.status === 401) { location.reload(); return; }
                const data = await res.json();
                
                const badge = document.getElementById('parental-status-badge');
                const desc = document.getElementById('current-dns-display');
                
                if (data.dns_enable && data.profile !== 'off') {
                    badge.innerHTML = `<span style="color:var(--success); display:inline-flex; align-items:center; gap:6px;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><path d="m9 12 2 2 4-4"/></svg>
                        فعال: ${data.profile_title}
                    </span>`;
                    desc.innerText = `${data.dns1} , ${data.dns2}`;
                } else {
                    badge.innerHTML = `<span style="color:var(--text-muted); display:inline-flex; align-items:center; gap:6px;">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="2" y1="2" x2="22" y2="22"/></svg>
                        غیرفعال (حالت پیش‌فرض اپراتور)
                    </span>`;
                    desc.innerText = 'خودکار (پیش‌فرض سیم‌کارت بدون فیلتر)';
                }

                if (data.profile === 'custom') {
                    if (data.dns1) document.getElementById('custom-dns1').value = data.dns1;
                    if (data.dns2) document.getElementById('custom-dns2').value = data.dns2;
                }

                loadParentalDevices();
            } catch (e) {
                console.error('loadParentalStatus error:', e);
            }
        }

        async function loadParentalDevices() {
            try {
                const res = await fetch('/api/devices');
                const data = await res.json();
                const container = document.getElementById('parental-devices-container');
                if (!container) return;
                
                const list = (data.devices || []).filter(d => d.status === 'online' || d.is_online);
                if (list.length === 0) {
                    container.innerHTML = '<div style="color:var(--text-muted); font-size:13px; grid-column:1/-1;">هیچ دستگاه آنلاینی یافت نشد.</div>';
                    return;
                }

                let html = '';
                list.forEach(d => {
                    const isSelf = d.is_host;
                    html += `
                    <div style="background:var(--input-bg); border:1px solid var(--border); border-radius:10px; padding:12px; display:flex; flex-direction:column; justify-content:space-between; gap:10px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div>
                                <div style="font-weight:700; font-size:13px; color:var(--text-main);">${escapeHtml(d.name)} ${isSelf ? '<span style="font-size:10px; color:var(--warning);">(دستگاه شما)</span>' : ''}</div>
                                <div style="font-size:11px; color:var(--text-muted); font-family:monospace; margin-top:2px;">${d.ip}</div>
                            </div>
                            <span style="font-size:10.5px; background:rgba(16,185,129,0.15); color:var(--success); padding:2px 6px; border-radius:4px; font-weight:700;">آنلاین</span>
                        </div>
                        <div style="font-size:11.5px; color:var(--text-muted); display:flex; justify-content:space-between;">
                            <span>مصرف کل: <strong>${d.traffic_str || '0 B'}</strong></span>
                            <span>مدت اتصال: <strong>${d.duration_str || '0'}</strong></span>
                        </div>
                        <div style="display:flex; gap:6px; margin-top:4px;">
                            ${isSelf ? '<span style="font-size:11px; color:var(--text-muted);">سیستم اصلی محافظت‌شده</span>' : `
                                <button class="btn-sm btn-danger" style="flex:1; justify-content:center; font-size:11px; padding:6px;" onclick="blockDevice('${d.mac}', '${escapeHtml(d.name)}')">
                                    قطع اینترنت (خواب کودک)
                                </button>
                                <button class="btn-sm btn-secondary" style="font-size:11px; padding:6px 10px;" onclick="disconnectDevice('${d.mac}', '${escapeHtml(d.name)}')">
                                    قطع موقت
                                </button>
                            `}
                        </div>
                    </div>
                    `;
                });
                container.innerHTML = html;
            } catch (e) {
                console.error('loadParentalDevices error:', e);
            }
        }

        async function applyDnsProfile(profile) {
            let msg = 'آیا مایل به اعمال این پروفایل محافظت روی مودم هستید؟';
            if (profile === 'off') {
                msg = 'آیا از غیرفعال‌سازی فیلتر محافظت کودکان اطمینان دارید؟';
            }
            if (!confirm(msg)) return;

            try {
                const res = await fetch('/api/dns/set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile: profile })
                });
                const data = await res.json();
                if (data.success) {
                    alert(data.message || 'تنظیمات با موفقیت اعمال شد.');
                    loadParentalStatus();
                } else {
                    alert(data.message || 'خطا در اعمال تنظیمات.');
                }
            } catch (e) {
                alert('خطا در برقراری ارتباط با سرور.');
            }
        }

        async function saveCustomDns() {
            const dns1 = document.getElementById('custom-dns1').value.trim();
            const dns2 = document.getElementById('custom-dns2').value.trim();
            if (!dns1) {
                alert('لطفاً حداقل آدرس DNS اول را وارد کنید.');
                return;
            }
            try {
                const res = await fetch('/api/dns/set', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ profile: 'custom', dns1: dns1, dns2: dns2 })
                });
                const data = await res.json();
                if (data.success) {
                    alert('DNS نظارتی با موفقیت روی مودم تنظیم شد.');
                    loadParentalStatus();
                } else {
                    alert(data.message || 'خطا در اعمال DNS.');
                }
            } catch (e) {
                alert('خطا در ذخیره DNS.');
            }
        }

        // ================= SECURITY & AUTHENTICATION =================
        function openPasswordModal() {
            document.getElementById('pwd-msg').style.display = 'none';
            document.getElementById('pwd-current').value = '';
            document.getElementById('pwd-new-user').value = '';
            document.getElementById('pwd-new').value = '';
            document.getElementById('pwd-confirm').value = '';
            document.getElementById('modal-password').classList.add('active');
        }

        function closePasswordModal() {
            document.getElementById('modal-password').classList.remove('active');
        }

        async function submitPasswordChange() {
            const currentPass = document.getElementById('pwd-current').value;
            const newUser = document.getElementById('pwd-new-user').value.trim();
            const newPass = document.getElementById('pwd-new').value;
            const confirmPass = document.getElementById('pwd-confirm').value;
            const msgDiv = document.getElementById('pwd-msg');

            msgDiv.style.display = 'none';

            if (!currentPass) {
                msgDiv.innerText = 'لطفاً رمز عبور فعلی را وارد کنید.';
                msgDiv.style.background = 'rgba(244, 63, 94, 0.15)';
                msgDiv.style.color = '#fb7185';
                msgDiv.style.display = 'block';
                return;
            }

            if (!newPass || newPass.length < 4) {
                msgDiv.innerText = 'رمز عبور جدید باید حداقل ۴ کاراکتر باشد.';
                msgDiv.style.background = 'rgba(244, 63, 94, 0.15)';
                msgDiv.style.color = '#fb7185';
                msgDiv.style.display = 'block';
                return;
            }

            if (newPass !== confirmPass) {
                msgDiv.innerText = 'رمز عبور جدید و تکرار آن یکسان نیستند.';
                msgDiv.style.background = 'rgba(244, 63, 94, 0.15)';
                msgDiv.style.color = '#fb7185';
                msgDiv.style.display = 'block';
                return;
            }

            try {
                const res = await fetch('/api/auth/change_password', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        current_password: currentPass,
                        new_username: newUser,
                        new_password: newPass
                    })
                });
                const data = await res.json();
                if (data.success) {
                    msgDiv.innerText = data.message || 'رمز عبور با موفقیت به‌روزرسانی شد.';
                    msgDiv.style.background = 'rgba(16, 185, 129, 0.15)';
                    msgDiv.style.color = '#34d399';
                    msgDiv.style.display = 'block';
                    setTimeout(() => { closePasswordModal(); }, 1800);
                } else {
                    msgDiv.innerText = data.message || 'خطا در تغییر رمز عبور.';
                    msgDiv.style.background = 'rgba(244, 63, 94, 0.15)';
                    msgDiv.style.color = '#fb7185';
                    msgDiv.style.display = 'block';
                }
            } catch (err) {
                msgDiv.innerText = 'خطا در برقراری ارتباط با سرور.';
                msgDiv.style.background = 'rgba(244, 63, 94, 0.15)';
                msgDiv.style.color = '#fb7185';
                msgDiv.style.display = 'block';
            }
        }

        async function handleLogout() {
            if (!confirm('آیا می‌خواهید از پنل مدیریت خارج شوید؟')) return;
            try {
                await fetch('/api/auth/logout', { method: 'POST' });
            } catch (e) {}
            window.location.reload();
        }

        // Init
        initTheme();
        refreshStatus();
        loadConversations();
        loadContacts();
        loadDevices();
        setInterval(refreshStatus, 2500);
        setInterval(loadConversations, 10000);
        setInterval(loadDevices, 15000);
    </script>
</body>
</html>
"""


class ModemDashboardHandler(http.server.BaseHTTPRequestHandler):
    def get_session_token(self):
        cookie_header = self.headers.get("Cookie", "")
        if not cookie_header:
            return None
        cookies = http.cookies.SimpleCookie()
        try:
            cookies.load(cookie_header)
            if "session_id" in cookies:
                return cookies["session_id"].value
        except Exception:
            pass
        return None

    def render_login_page(self):
        encoded = LOGIN_PAGE.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            self.wfile.write(encoded)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json(self, data, status=200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_json_with_cookie(self, data, cookie_str, status=200):
        try:
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Set-Cookie", cookie_str)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

    def do_GET(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        session_id = self.get_session_token()
        is_authed = auth_manager.is_valid_session(session_id)

        if not is_authed:
            if path in ["/", "/index.html"]:
                self.render_login_page()
                return
            else:
                self.send_json({"error": "Unauthorized"}, status=401)
                return

        if path == "/" or path == "/index.html":
            encoded = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(encoded)))
            self.send_header("Connection", "close")
            self.end_headers()
            try:
                self.wfile.write(encoded)
            except (BrokenPipeError, ConnectionResetError):
                pass
            return

        elif path == "/api/status":
            data = client.get_status()
            self.send_json(data or {})
            return

        elif path == "/api/conversations":
            data = client.get_conversations()
            self.send_json(data)
            return

        elif path == "/api/contacts":
            contacts = client.get_phonebook()
            self.send_json(contacts)
            return

        elif path == "/api/devices":
            dev_data = client.get_connected_devices()
            dev_data["current_client_ip"] = self.client_address[0]
            self.send_json(dev_data)
            return

        elif path == "/api/sms":
            sms_data = client.get_sms_list(page=1, data_per_page=50)
            self.send_json(sms_data)
            return

        elif path == "/api/dns":
            dns_data = client.get_dhcp_info()
            self.send_json(dns_data)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b"{}"

        try:
            payload = json.loads(body.decode("utf-8"))
        except Exception:
            payload = {}

        # Handle login (unauthenticated endpoint)
        if path == "/api/auth/login":
            client_ip = self.client_address[0]
            username = payload.get("username", "")
            password = payload.get("password", "")
            success, token, msg = auth_manager.login(username, password, client_ip)
            if success and token:
                cookie_header = f"session_id={token}; Path=/; Max-Age={30*86400}; HttpOnly; SameSite=Lax"
                self.send_json_with_cookie({"success": True}, cookie_header)
            else:
                self.send_json({"success": False, "message": msg}, status=401)
            return

        # Authenticate all other POST requests
        session_id = self.get_session_token()
        if not auth_manager.is_valid_session(session_id):
            self.send_json({"error": "Unauthorized"}, status=401)
            return

        if path == "/api/auth/logout":
            auth_manager.revoke_session(session_id)
            cookie_header = "session_id=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax"
            self.send_json_with_cookie({"success": True}, cookie_header)
            return

        elif path == "/api/auth/change_password":
            old_pass = payload.get("current_password", "")
            new_user = payload.get("new_username", "")
            new_pass = payload.get("new_password", "")
            success, msg = auth_manager.change_credentials(old_pass, new_user, new_pass)
            self.send_json({"success": success, "message": msg})
            return

        elif path == "/api/devices/block":
            mac = payload.get("mac", "")
            success = client.set_device_management(2, mac)
            self.send_json({"success": success})
            return

        elif path == "/api/devices/unblock":
            mac = payload.get("mac", "")
            success = client.set_device_management(3, mac)
            self.send_json({"success": success})
            return

        elif path == "/api/devices/disconnect":
            mac = payload.get("mac", "")
            success = client.set_device_management(1, mac)
            self.send_json({"success": success})
            return

        elif path == "/api/devices/reset_traffic":
            success = client.set_device_management(4)
            self.send_json({"success": success})
            return

        elif path == "/api/dns/set":
            profile = payload.get("profile", "off")
            dns1 = payload.get("dns1", "")
            dns2 = payload.get("dns2", "")
            res = client.set_dns_config(profile, dns1, dns2)
            self.send_json(res)
            return

        elif path == "/api/send_sms":
            phone = payload.get("phone", "")
            text = payload.get("text", "")
            success = client.send_sms(phone, text)
            self.send_json({"success": success})
            return

        elif path == "/api/contacts/add":
            name = payload.get("name", "")
            number = payload.get("number", "")
            group = payload.get("group", "common")
            loc = payload.get("location", "0")
            success = client.add_contact(name, number, group=group, location=loc)
            self.send_json({"success": success})
            return

        elif path == "/api/contacts/delete":
            cid = payload.get("id", "")
            success = client.delete_contact(cid)
            self.send_json({"success": success})
            return

        elif path == "/api/mark_read":
            msg_id = payload.get("id", "")
            success = client.mark_sms_as_read(msg_id)
            self.send_json({"success": success})
            return

        elif path == "/api/mark_conversation_read":
            ids = payload.get("ids", [])
            marked = 0
            for mid in ids:
                if client.mark_sms_as_read(mid):
                    marked += 1
            self.send_json({"success": True, "marked_count": marked})
            return

        elif path == "/api/mark_all_read":
            count = client.mark_all_sms_as_read()
            self.send_json({"success": True, "marked_count": count})
            return

        elif path == "/api/delete_sms":
            msg_id = payload.get("id", "")
            success = client.delete_sms(msg_id)
            self.send_json({"success": success})
            return

        elif path == "/api/delete_all_sms":
            count = client.delete_all_sms()
            self.send_json({"success": True, "deleted_count": count})
            return

        elif path == "/api/ussd":
            code = payload.get("code", "")
            result = client.send_ussd(code)
            self.send_json({"result": result})
            return

        elif path == "/api/reboot":
            success = client.reboot()
            self.send_json({"success": success})
            return

        self.send_error(404, "Not Found")

    def log_message(self, format, *args):
        return


class ThreadedHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def run_server():
    with ThreadedHTTPServer(("0.0.0.0", PORT), ModemDashboardHandler) as httpd:
        print(f"Modem Dashboard running at http://0.0.0.0:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
