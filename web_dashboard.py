#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Local Modern Web Dashboard for NWR-945X Modem
Run on http://127.0.0.1:8080
Provides:
- SMS Inbox & Outbox reader
- SMS Sender
- Missed Call Monitor
- USSD Dialing
- Live Modem & Battery Telemetry
- Device Reboot
"""

import http.server
import socketserver
import json
import urllib.parse
from modem_client import ModemClient

PORT = 8080
client = ModemClient()

HTML_PAGE = """<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>مدیریت هوشمند مودم NWR-945X</title>
    <style>
        :root {
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --accent: #38bdf8;
            --accent-glow: rgba(56, 189, 248, 0.25);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --danger: #f43f5e;
            --success: #10b981;
            --warning: #f59e0b;
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Vazirmatn", Tahoma, sans-serif;
        }

        body {
            background-color: var(--bg);
            background-image: 
                radial-gradient(at 0% 0%, rgba(56, 189, 248, 0.12) 0px, transparent 50%),
                radial-gradient(at 100% 100%, rgba(139, 92, 246, 0.12) 0px, transparent 50%);
            color: var(--text-main);
            min-height: 100vh;
            padding: 24px;
            direction: rtl;
        }

        .container {
            max-width: 1000px;
            margin: 0 auto;
        }

        header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
            margin-bottom: 24px;
        }

        .logo-area {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .logo-badge {
            width: 44px;
            height: 44px;
            background: linear-gradient(135deg, #0284c7, #38bdf8);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 4px 14px var(--accent-glow);
        }

        h1 {
            font-size: 20px;
            font-weight: 700;
        }

        .subtitle {
            font-size: 13px;
            color: var(--text-muted);
        }

        /* Status Bar Cards */
        .grid-stats {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }

        .stat-card {
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 16px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: transform 0.2s, border-color 0.2s;
        }

        .stat-card:hover {
            transform: translateY(-2px);
            border-color: rgba(56, 189, 248, 0.3);
        }

        .stat-label {
            font-size: 13px;
            color: var(--text-muted);
            display: flex;
            align-items: center;
            gap: 6px;
        }

        .stat-val {
            font-size: 22px;
            font-weight: 700;
        }

        /* Navigation Tabs */
        .tabs {
            display: flex;
            gap: 10px;
            background: rgba(15, 23, 42, 0.6);
            padding: 6px;
            border-radius: 14px;
            border: 1px solid var(--border);
            margin-bottom: 24px;
        }

        .tab-btn {
            flex: 1;
            padding: 10px 16px;
            background: transparent;
            border: none;
            color: var(--text-muted);
            font-size: 14px;
            font-weight: 600;
            border-radius: 10px;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 8px;
        }

        .tab-btn.active {
            background: var(--accent);
            color: #0f172a;
            box-shadow: 0 4px 12px var(--accent-glow);
        }

        /* Content Sections */
        .tab-content {
            display: none;
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 24px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
        }

        .tab-content.active {
            display: block;
            animation: fadeIn 0.25s ease-in-out;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(6px); }
            to { opacity: 1; transform: translateY(0); }
        }

        /* SMS List */
        .sms-item {
            padding: 16px;
            border-radius: 14px;
            border: 1px solid var(--border);
            background: rgba(15, 23, 42, 0.4);
            margin-bottom: 12px;
            display: flex;
            flex-direction: column;
            gap: 8px;
            transition: border-color 0.2s;
        }

        .sms-item:hover {
            border-color: rgba(56, 189, 248, 0.4);
        }

        .sms-item.missed-call {
            border-right: 4px solid var(--danger);
            background: rgba(244, 63, 94, 0.05);
        }

        .sms-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .sender-tag {
            font-weight: 700;
            color: var(--accent);
            font-size: 15px;
            direction: ltr;
            text-align: right;
        }

        .badge {
            font-size: 11px;
            padding: 3px 8px;
            border-radius: 6px;
            font-weight: 600;
        }

        .badge-call {
            background: rgba(244, 63, 94, 0.2);
            color: #fda4af;
        }

        .badge-sms {
            background: rgba(56, 189, 248, 0.2);
            color: #7dd3fc;
        }

        .sms-time {
            font-size: 12px;
            color: var(--text-muted);
            direction: ltr;
        }

        .sms-body {
            font-size: 14px;
            line-height: 1.6;
            color: #e2e8f0;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .sms-actions {
            display: flex;
            justify-content: flex-end;
            gap: 8px;
            margin-top: 4px;
        }

        /* Buttons & Forms */
        .btn {
            padding: 8px 16px;
            border-radius: 10px;
            border: none;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }

        .btn-primary {
            background: var(--accent);
            color: #0f172a;
        }

        .btn-primary:hover {
            opacity: 0.9;
            transform: scale(0.98);
        }

        .btn-danger {
            background: rgba(244, 63, 94, 0.15);
            color: #fda4af;
            border: 1px solid rgba(244, 63, 94, 0.3);
        }

        .btn-danger:hover {
            background: var(--danger);
            color: #fff;
        }

        .form-group {
            margin-bottom: 16px;
        }

        label {
            display: block;
            margin-bottom: 8px;
            font-size: 13px;
            color: var(--text-muted);
            font-weight: 500;
        }

        input, textarea {
            width: 100%;
            padding: 12px 14px;
            border-radius: 10px;
            background: rgba(15, 23, 42, 0.7);
            border: 1px solid var(--border);
            color: #fff;
            font-size: 14px;
            outline: none;
            transition: border-color 0.2s;
        }

        input:focus, textarea:focus {
            border-color: var(--accent);
        }

        .ussd-quick {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-bottom: 16px;
        }

        .ussd-chip {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid var(--border);
            padding: 6px 12px;
            border-radius: 8px;
            color: #cbd5e1;
            font-size: 13px;
            cursor: pointer;
            transition: all 0.2s;
        }

        .ussd-chip:hover {
            border-color: var(--accent);
            color: var(--accent);
        }

        #ussd-output {
            background: rgba(15, 23, 42, 0.8);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
            min-height: 80px;
            font-size: 14px;
            line-height: 1.6;
            white-space: pre-wrap;
            color: #e2e8f0;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <div class="logo-area">
                <div class="logo-badge">📶</div>
                <div>
                    <h1>مودم شارژی NWR-945X</h1>
                    <div class="subtitle">پنل مدیریت هوشمند پیامک‌ها، تماس‌ها و وضعیت باتری</div>
                </div>
            </div>
            <div>
                <button class="btn btn-primary" onclick="refreshStatus()">🔄 بروزرسانی</button>
            </div>
        </header>

        <!-- Stats Bar -->
        <div class="grid-stats">
            <div class="stat-card">
                <div class="stat-label">🔋 درصد شارژ باتری</div>
                <div class="stat-val" id="stat-battery">--%</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">⚡ وضعیت شارژر</div>
                <div class="stat-val" id="stat-charging">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">👥 دستگاه‌های متصل</div>
                <div class="stat-val" id="stat-clients">--</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">📶 کیفیت آنتن</div>
                <div class="stat-val" id="stat-signal">-- / ۵</div>
            </div>
        </div>

        <!-- Navigation Tabs -->
        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('inbox')">📥 پیامک‌ها و تماس‌ها</button>
            <button class="tab-btn" onclick="switchTab('send')">✏️ ارسال پیامک جدید</button>
            <button class="tab-btn" onclick="switchTab('ussd')">🔢 کدهای دستوری (USSD)</button>
            <button class="tab-btn" onclick="switchTab('control')">⚙️ کنترل مودم</button>
        </div>

        <!-- Tab 1: Inbox & Missed Calls -->
        <div id="tab-inbox" class="tab-content active">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px;">
                <h3 style="font-size: 16px;">صندوق پیامک‌های دریافتی</h3>
                <span id="unread-count-badge" class="badge badge-sms">۰ خوانده‌نشده</span>
            </div>
            <div id="sms-container">در حال دریافت پیامک‌ها...</div>
        </div>

        <!-- Tab 2: Send SMS -->
        <div id="tab-send" class="tab-content">
            <h3 style="font-size: 16px; margin-bottom: 16px;">ارسال پیامک جدید</h3>
            <div class="form-group">
                <label>شماره تماس گیرنده (مثلاً 09123456789)</label>
                <input type="text" id="send-phone" placeholder="09xxxxxxxxx">
            </div>
            <div class="form-group">
                <label>متن پیامک</label>
                <textarea id="send-text" rows="4" placeholder="متن پیامک را اینجا بنویسید..."></textarea>
            </div>
            <button class="btn btn-primary" id="btn-send-sms" onclick="handleSendSMS()">📤 ارسال پیامک</button>
            <span id="send-status" style="margin-right: 12px; font-size: 13px;"></span>
        </div>

        <!-- Tab 3: USSD -->
        <div id="tab-ussd" class="tab-content">
            <h3 style="font-size: 16px; margin-bottom: 16px;">استعلام بسته و شارژ (کدهای USSD)</h3>
            <div class="ussd-quick">
                <span class="ussd-chip" onclick="setUSSD('*100#')">*100# (منوی اصلی)</span>
                <span class="ussd-chip" onclick="setUSSD('*140*11#')">*140*11# (مانده اعتبار)</span>
                <span class="ussd-chip" onclick="setUSSD('*1#')">*1# (شارژ و بسته)</span>
                <span class="ussd-chip" onclick="setUSSD('*141*1#')">*141*1# (استعلام ایرانسل)</span>
            </div>
            <div style="display: flex; gap: 8px; margin-bottom: 16px;">
                <input type="text" id="ussd-code" placeholder="کد دستوری (مثلاً *100#)" style="direction: ltr;">
                <button class="btn btn-primary" onclick="handleUSSD()">شماره‌گیری</button>
            </div>
            <label>نتیجه استعلام:</label>
            <div id="ussd-output">برای مشاهده پاسخ، کد دستوری را وارد کرده و شماره‌گیری کنید.</div>
        </div>

        <!-- Tab 4: Control -->
        <div id="tab-control" class="tab-content">
            <h3 style="font-size: 16px; margin-bottom: 16px;">عملیات و مدیریت مودم</h3>
            <p style="color: var(--text-muted); font-size: 14px; margin-bottom: 20px;">
                از این قسمت می‌توانید مودم را ری‌استارت کرده یا مستقیماً به صفحه تنظیمات داخلی آن دسترسی پیدا کنید.
            </p>
            <div style="display: flex; gap: 12px;">
                <button class="btn btn-danger" onclick="handleReboot()">🔄 ری‌استارت کردن مودم</button>
                <a href="http://192.168.1.1" target="_blank" class="btn btn-primary" style="text-decoration: none;">🌐 باز کردن پنل اصلی مودم</a>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tab) {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
            event.currentTarget.classList.add('active');
            document.getElementById('tab-' + tab).classList.add('active');
            if (tab === 'inbox') loadSMS();
        }

        async function refreshStatus() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data) {
                    document.getElementById('stat-battery').innerText = (data.battery_percent || '0') + '%';
                    document.getElementById('stat-charging').innerText = (data.battery_charging === '1') ? 'متصل به شارژر ⚡' : 'درحال مصرف باتری';
                    document.getElementById('stat-clients').innerText = data.wifi_clients_num || '0';
                    document.getElementById('stat-signal').innerText = (data.signal_quality || '0') + ' / ۵';
                    document.getElementById('unread-count-badge').innerText = (data.unread_long || '0') + ' خوانده‌نشده';
                }
            } catch (e) {
                console.error(e);
            }
        }

        async function loadSMS() {
            const container = document.getElementById('sms-container');
            container.innerHTML = '<div style="color:var(--text-muted); padding:20px; text-align:center;">در حال بارگذاری پیامک‌ها...</div>';
            try {
                const res = await fetch('/api/sms');
                const data = await res.json();
                const list = data.messages || [];
                if (list.length === 0) {
                    container.innerHTML = '<div style="padding:20px; text-align:center;">پیامکی موجود نیست.</div>';
                    return;
                }
                let html = '';
                list.forEach(m => {
                    const isCall = m.is_missed_call;
                    const badge = isCall ? '<span class="badge badge-call">📞 تماس بی‌پاسخ</span>' : '<span class="badge badge-sms">💬 پیامک</span>';
                    const callClass = isCall ? 'missed-call' : '';
                    html += `
                        <div class="sms-item ${callClass}">
                            <div class="sms-header">
                                <div style="display:flex; align-items:center; gap:8px;">
                                    ${badge}
                                    <span class="sender-tag">${m.sender}</span>
                                </div>
                                <span class="sms-time">${m.time}</span>
                            </div>
                            <div class="sms-body">${m.text}</div>
                            <div class="sms-actions">
                                <button class="btn btn-primary" onclick="replySMS('${m.sender}')" style="padding:4px 10px; font-size:12px;">پاسخ</button>
                                <button class="btn btn-danger" onclick="deleteSMS('${m.id}')" style="padding:4px 10px; font-size:12px;">حذف</button>
                            </div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            } catch (e) {
                container.innerHTML = '<div style="color:var(--danger); padding:20px;">خطا در دریافت پیامک‌ها. اتصال به مودم را بررسی کنید.</div>';
            }
        }

        function replySMS(sender) {
            document.querySelectorAll('.tab-btn')[1].click();
            document.getElementById('send-phone').value = sender;
            document.getElementById('send-text').focus();
        }

        async function handleSendSMS() {
            const phone = document.getElementById('send-phone').value.trim();
            const text = document.getElementById('send-text').value.trim();
            const statusEl = document.getElementById('send-status');
            const btn = document.getElementById('btn-send-sms');
            if (!phone || !text) {
                alert('لطفاً شماره گیرنده و متن پیامک را وارد کنید.');
                return;
            }
            btn.disabled = true;
            statusEl.innerText = 'در حال ارسال...';
            try {
                const res = await fetch('/api/send_sms', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({phone, text})
                });
                const data = await res.json();
                if (data.success) {
                    statusEl.innerText = '✅ با موفقیت ارسال شد.';
                    statusEl.style.color = 'var(--success)';
                    document.getElementById('send-text').value = '';
                } else {
                    statusEl.innerText = '❌ خطا در ارسال پیامک.';
                    statusEl.style.color = 'var(--danger)';
                }
            } catch (e) {
                statusEl.innerText = '❌ خطا در برقراری ارتباط.';
            } finally {
                btn.disabled = false;
            }
        }

        function setUSSD(code) {
            document.getElementById('ussd-code').value = code;
        }

        async function handleUSSD() {
            const code = document.getElementById('ussd-code').value.trim();
            const output = document.getElementById('ussd-output');
            if (!code) return;
            output.innerText = 'در حال ارسال کد به شبکه و دریافت پاسخ... (چند ثانیه صبور باشید)';
            try {
                const res = await fetch('/api/ussd', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({code})
                });
                const data = await res.json();
                output.innerText = data.result || 'بدون پاسخ';
            } catch (e) {
                output.innerText = 'خطا در ارتباط با مودم.';
            }
        }

        async function deleteSMS(id) {
            if (!confirm('آیا از حذف این پیامک مطمئن هستید؟')) return;
            try {
                await fetch('/api/delete_sms', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({id})
                });
                loadSMS();
            } catch (e) {
                alert('خطا در حذف پیامک');
            }
        }

        async function handleReboot() {
            if (!confirm('آیا مطمئن هستید که می‌خواهید مودم را ری‌استارت کنید؟')) return;
            await fetch('/api/reboot', {method: 'POST'});
            alert('دستور ری‌استارت ارسال شد. اتصال مودم برای حدود ۱ دقیقه قطع خواهد شد.');
        }

        // Init
        refreshStatus();
        loadSMS();
        setInterval(refreshStatus, 15000);
    </script>
</body>
</html>"""


class ModemDashboardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        url_parsed = urllib.parse.urlparse(self.path)
        path = url_parsed.path

        if path == "/" or path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode("utf-8"))
            return

        elif path == "/api/status":
            data = client.get_status()
            self.send_json(data or {})
            return

        elif path == "/api/sms":
            sms_data = client.get_sms_list(page=1, data_per_page=30)
            self.send_json(sms_data)
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

        if path == "/api/send_sms":
            phone = payload.get("phone", "")
            text = payload.get("text", "")
            success = client.send_sms(phone, text)
            self.send_json({"success": success})
            return

        elif path == "/api/ussd":
            code = payload.get("code", "")
            result = client.send_ussd(code)
            self.send_json({"result": result})
            return

        elif path == "/api/delete_sms":
            msg_id = payload.get("id", "")
            success = client.delete_sms(msg_id)
            self.send_json({"success": success})
            return

        elif path == "/api/reboot":
            success = client.reboot()
            self.send_json({"success": success})
            return

        self.send_error(404, "Not Found")

    def send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # Silence default access logging to keep terminal clean
        return


def run_server():
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), ModemDashboardHandler) as httpd:
        print(f"Modem Dashboard running at http://127.0.0.1:{PORT}")
        httpd.serve_forever()


if __name__ == "__main__":
    run_server()
