#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generates the HTML/CSS/JS for the standalone LAN Chat & Call Room.
Accessible without admin login on LAN.
"""

def build_room_page(room_id: str, room_title: str) -> str:
    escaped_title = room_title.replace('"', '&quot;').replace('<', '&lt;')
    escaped_id = room_id.replace('"', '&quot;').replace('<', '&lt;')
    
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
    <title>{escaped_title} - چت و تماس شبکه محلی</title>
    <style>
        @font-face {{
            font-family: 'Vazirmatn';
            src: url('/static/fonts/Vazirmatn-Regular.ttf') format('truetype');
            font-weight: 400;
        }}
        @font-face {{
            font-family: 'Vazirmatn';
            src: url('/static/fonts/Vazirmatn-Medium.ttf') format('truetype');
            font-weight: 500;
        }}
        @font-face {{
            font-family: 'Vazirmatn';
            src: url('/static/fonts/Vazirmatn-Bold.ttf') format('truetype');
            font-weight: 700;
        }}
        :root {{
            --bg-body: #090d16;
            --bg-card: rgba(22, 29, 47, 0.75);
            --bg-input: #121829;
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(168, 85, 247, 0.4);
            --primary: #a855f7;
            --primary-grad: linear-gradient(135deg, #a855f7, #6366f1);
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --my-bubble: linear-gradient(135deg, #7c3aed, #4f46e5);
            --other-bubble: rgba(30, 41, 59, 0.85);
            --system-bubble: rgba(255, 255, 255, 0.05);
            --accent-green: #10b981;
            --danger: #ef4444;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: 'Vazirmatn', -apple-system, sans-serif; }}
        body {{
            background: var(--bg-body);
            color: var(--text-main);
            height: 100vh;
            height: 100dvh;
            display: flex;
            flex-direction: column;
            overflow: hidden;
        }}
        /* Top Header */
        header {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border-bottom: 1px solid var(--border);
            padding: 12px 18px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
            flex-shrink: 0;
            z-index: 10;
        }}
        .header-title-box {{
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }}
        .room-icon {{
            width: 42px;
            height: 42px;
            border-radius: 12px;
            background: var(--primary-grad);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            flex-shrink: 0;
            box-shadow: 0 4px 14px rgba(168, 85, 247, 0.3);
        }}
        .room-name {{
            font-size: 15px;
            font-weight: 800;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .lan-badge {{
            display: inline-flex;
            align-items: center;
            gap: 5px;
            font-size: 11px;
            color: var(--accent-green);
            background: rgba(16, 185, 129, 0.1);
            padding: 2px 8px;
            border-radius: 12px;
            border: 1px solid rgba(16, 185, 129, 0.2);
        }}
        .header-actions {{
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .btn-call {{
            padding: 8px 14px;
            border-radius: 10px;
            border: 1px solid var(--border);
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-main);
            cursor: pointer;
            font-size: 12.5px;
            font-weight: 600;
            display: inline-flex;
            align-items: center;
            gap: 6px;
            transition: all 0.2s;
        }}
        .btn-call:hover {{
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--border-hover);
        }}
        .btn-call.video {{
            background: rgba(99, 102, 241, 0.15);
            color: #818cf8;
            border-color: rgba(99, 102, 241, 0.3);
        }}
        .btn-call.voice {{
            background: rgba(16, 185, 129, 0.15);
            color: #34d399;
            border-color: rgba(16, 185, 129, 0.3);
        }}

        /* Chat Body & Scroll Area */
        #chat-container {{
            flex: 1;
            overflow-y: auto;
            padding: 20px 18px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            scroll-behavior: smooth;
        }}
        .msg-row {{
            display: flex;
            flex-direction: column;
            max-width: 82%;
            animation: fadeIn 0.15s ease-out;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(6px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .msg-row.mine {{
            align-self: flex-start; /* in RTL, align-self: flex-start puts it on the right! */
        }}
        .msg-row.other {{
            align-self: flex-end; /* in RTL, flex-end puts it on the left! */
        }}
        .msg-sender {{
            font-size: 11px;
            margin-bottom: 4px;
            padding: 0 4px;
            font-weight: 700;
        }}
        .msg-bubble {{
            padding: 10px 14px;
            border-radius: 16px;
            font-size: 13.5px;
            line-height: 1.6;
            word-break: break-word;
            position: relative;
            box-shadow: 0 2px 10px rgba(0, 0, 0, 0.15);
        }}
        .msg-row.mine .msg-bubble {{
            background: var(--my-bubble);
            color: #ffffff;
            border-bottom-right-radius: 4px;
        }}
        .msg-row.other .msg-bubble {{
            background: var(--other-bubble);
            color: var(--text-main);
            border: 1px solid var(--border);
            border-bottom-left-radius: 4px;
        }}
        .msg-meta {{
            font-size: 10px;
            color: rgba(255, 255, 255, 0.65);
            margin-top: 4px;
            text-align: left;
            direction: ltr;
        }}
        .msg-system {{
            align-self: center;
            background: var(--system-bubble);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 5px 14px;
            font-size: 11.5px;
            color: var(--text-muted);
            text-align: center;
            margin: 4px 0;
        }}
        .file-attach-card {{
            display: flex;
            align-items: center;
            gap: 10px;
            background: rgba(0, 0, 0, 0.2);
            padding: 8px 12px;
            border-radius: 10px;
            margin-top: 6px;
            border: 1px solid rgba(255, 255, 255, 0.1);
        }}
        .file-attach-btn {{
            background: var(--primary-grad);
            color: white;
            padding: 5px 10px;
            border-radius: 6px;
            font-size: 11px;
            text-decoration: none;
            font-weight: bold;
            white-space: nowrap;
        }}

        /* Bottom Input Bar */
        footer {{
            background: var(--bg-card);
            backdrop-filter: blur(12px);
            border-top: 1px solid var(--border);
            padding: 12px 18px;
            display: flex;
            align-items: flex-end;
            gap: 10px;
            flex-shrink: 0;
        }}
        .input-box {{
            flex: 1;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 14px;
            padding: 8px 14px;
            display: flex;
            align-items: center;
            gap: 8px;
            transition: border 0.2s;
        }}
        .input-box:focus-within {{
            border-color: var(--primary);
        }}
        .chat-input {{
            flex: 1;
            background: transparent;
            border: none;
            outline: none;
            color: var(--text-main);
            font-size: 14px;
            resize: none;
            max-height: 100px;
            line-height: 1.5;
        }}
        .btn-icon {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 6px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: all 0.2s;
        }}
        .btn-icon:hover {{
            color: var(--text-main);
            background: rgba(255, 255, 255, 0.08);
        }}
        .btn-send {{
            background: var(--primary-grad);
            border: none;
            color: white;
            width: 44px;
            height: 44px;
            border-radius: 12px;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            flex-shrink: 0;
            box-shadow: 0 4px 12px rgba(168, 85, 247, 0.3);
            transition: transform 0.1s;
        }}
        .btn-send:active {{ transform: scale(0.95); }}

        /* Modal: Nickname Entry */
        #modal-nickname {{
            position: fixed;
            inset: 0;
            background: rgba(0, 0, 0, 0.75);
            backdrop-filter: blur(8px);
            z-index: 999;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .modal-card {{
            background: #151b2c;
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 28px;
            width: 360px;
            max-width: 100%;
            text-align: center;
            box-shadow: 0 20px 50px rgba(0, 0, 0, 0.5);
        }}
        .modal-input {{
            width: 100%;
            background: var(--bg-input);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 12px 14px;
            color: var(--text-main);
            font-size: 14px;
            margin: 18px 0;
            outline: none;
            text-align: center;
        }}
        .modal-input:focus {{ border-color: var(--primary); }}
        .btn-join {{
            width: 100%;
            background: var(--primary-grad);
            border: none;
            color: white;
            padding: 12px;
            border-radius: 12px;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
        }}

        /* WebRTC Call Overlay */
        #call-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(5, 8, 15, 0.96);
            backdrop-filter: blur(16px);
            z-index: 1000;
            display: none;
            flex-direction: column;
            align-items: center;
            justify-content: space-between;
            padding: 30px 20px;
        }}
        .video-grid {{
            width: 100%;
            max-width: 900px;
            flex: 1;
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 20px;
            overflow: hidden;
            background: #000;
        }}
        #remote-video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
        }}
        #local-video {{
            position: absolute;
            bottom: 20px;
            left: 20px;
            width: 160px;
            height: 120px;
            border-radius: 12px;
            object-fit: cover;
            border: 2px solid var(--primary);
            box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
            background: #111;
        }}
        .call-controls {{
            display: flex;
            align-items: center;
            gap: 18px;
            margin-top: 20px;
        }}
        .btn-ctrl {{
            width: 54px;
            height: 54px;
            border-radius: 50%;
            border: none;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 18px;
            transition: all 0.2s;
        }}
        .btn-end {{ background: var(--danger); }}
        .btn-mute {{ background: rgba(255, 255, 255, 0.15); }}
        .btn-mute.active {{ background: #f59e0b; }}

        /* Ringing Modal */
        #modal-ring {{
            position: fixed;
            top: 20px;
            left: 50%;
            transform: translateX(-50%);
            background: #1e293b;
            border: 1px solid var(--border-hover);
            border-radius: 16px;
            padding: 16px 22px;
            z-index: 1100;
            display: none;
            align-items: center;
            gap: 16px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
            animation: bounceIn 0.3s ease-out;
        }}
        @keyframes bounceIn {{
            from {{ transform: translate(-50%, -30px); opacity: 0; }}
            to {{ transform: translate(-50%, 0); opacity: 1; }}
        }}
        .btn-ring-accept {{
            background: var(--accent-green);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 10px;
            font-weight: 700;
            cursor: pointer;
        }}
        .btn-ring-reject {{
            background: var(--danger);
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 10px;
            font-weight: 700;
            cursor: pointer;
        }}
    </style>
</head>
<body>

    <!-- Header -->
    <header>
        <div class="header-title-box">
            <div class="room-icon">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            </div>
            <div>
                <div class="room-name">{escaped_title}</div>
                <div class="lan-badge">
                    <span style="width:6px;height:6px;border-radius:50%;background:var(--accent-green);display:inline-block;"></span>
                    شبکه محلی LAN &bull; ۰ ریال اینترنت
                </div>
            </div>
        </div>
        <div class="header-actions">
            <button class="btn-call voice" onclick="initiateCall('voice')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                تماس صوتی
            </button>
            <button class="btn-call video" onclick="initiateCall('video')">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
                تماس تصویری
            </button>
        </div>
    </header>

    <!-- Chat Messages Feed -->
    <div id="chat-container"></div>

    <!-- Footer Input Bar -->
    <footer>
        <div class="input-box">
            <input type="file" id="file-input" style="display:none;" onchange="handleFileUpload(this)">
            <button class="btn-icon" onclick="document.getElementById('file-input').click()" title="ارسال فایل">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/></svg>
            </button>
            <textarea id="msg-input" class="chat-input" rows="1" placeholder="پیام خود را بنویسید..." onkeydown="handleInputKey(event)"></textarea>
        </div>
        <button class="btn-send" onclick="sendTextMessage()" title="ارسال">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="transform:rotate(180deg);"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
        </button>
    </footer>

    <!-- Nickname Modal -->
    <div id="modal-nickname">
        <div class="modal-card">
            <div class="room-icon" style="margin: 0 auto 16px auto; width: 54px; height: 54px;">
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
            </div>
            <h3 style="font-size:17px;font-weight:800;margin-bottom:6px;">ورود به اتاق گفتگو</h3>
            <p style="font-size:12px;color:var(--text-muted);">یک نام نمایشی برای سایر کاربران شبکه انتخاب کنید</p>
            <input type="text" id="nickname-input" class="modal-input" placeholder="نام یا نام مستعار..." onkeydown="if(event.key==='Enter')joinRoom();">
            <button class="btn-join" onclick="joinRoom()">ورود به چت‌روم</button>
        </div>
    </div>

    <!-- Ringing Modal -->
    <div id="modal-ring">
        <div style="font-size:13px;font-weight:700;" id="ring-caller-text">تماس ورودی...</div>
        <div style="display:flex;gap:8px;">
            <button class="btn-ring-accept" onclick="acceptCall()">پاسخ</button>
            <button class="btn-ring-reject" onclick="rejectCall()">رد</button>
        </div>
    </div>

    <!-- Call Overlay -->
    <div id="call-overlay">
        <div style="font-size:14px;color:var(--text-muted);font-weight:700;" id="call-status">در حال تماس...</div>
        <div class="video-grid">
            <video id="remote-video" autoplay playsinline></video>
            <video id="local-video" autoplay playsinline muted></video>
        </div>
        <div class="call-controls">
            <button class="btn-ctrl btn-mute" id="btn-toggle-mic" onclick="toggleMic()">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="23"/><line x1="8" y1="23" x2="16" y2="23"/></svg>
            </button>
            <button class="btn-ctrl btn-end" onclick="endCall()">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10.68 13.31a16 16 0 0 0 3.41 2.6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7 2 2 0 0 1 1.72 2v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.42 19.42 0 0 1-3.33-2.67m-2.67-3.34a19.79 19.79 0 0 1-3.07-8.63A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91"/><line x1="23" y1="1" x2="1" y2="23"/></svg>
            </button>
        </div>
    </div>

    <script>
        const ROOM_ID = "{escaped_id}";
        let clientId = localStorage.getItem('lan_client_id_' + ROOM_ID) || '';
        let myName = localStorage.getItem('lan_nick') || '';
        let lastMsgSeq = 0;
        let lastSigSeq = 0;
        let participants = [];
        let peerConn = null;
        let localStream = null;
        let pendingCall = null;
        let activeCallWith = null;

        window.onload = () => {{
            if (myName) {{
                document.getElementById('nickname-input').value = myName;
                joinRoom();
            }}
        }};

        async function joinRoom() {{
            const nick = (document.getElementById('nickname-input').value || '').trim();
            if (!nick) return;
            myName = nick;
            localStorage.setItem('lan_nick', myName);

            try {{
                const res = await fetch('/api/lan/chat/join', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ room_id: ROOM_ID, nickname: myName, client_id: clientId }})
                }});
                const data = await res.json();
                if (data.ok) {{
                    clientId = data.client_id;
                    localStorage.setItem('lan_client_id_' + ROOM_ID, clientId);
                    document.getElementById('modal-nickname').style.display = 'none';
                    if (data.messages) {{
                        renderMessages(data.messages);
                        lastMsgSeq = data.next_msg_seq || 0;
                    }}
                    startPolling();
                }}
            }} catch(e) {{
                console.error("Join failed", e);
            }}
        }}

        function handleInputKey(e) {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                sendTextMessage();
            }}
        }}

        async function sendTextMessage() {{
            const inp = document.getElementById('msg-input');
            const text = (inp.value || '').trim();
            if (!text || !clientId) return;
            inp.value = '';

            try {{
                await fetch('/api/lan/chat/message', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ room_id: ROOM_ID, client_id: clientId, text: text }})
                }});
            }} catch(e) {{
                console.error(e);
            }}
        }}

        async function handleFileUpload(input) {{
            const file = input.files[0];
            if (!file || !clientId) return;
            try {{
                await fetch(`/api/lan/chat/upload?room_id=${{ROOM_ID}}&client_id=${{clientId}}`, {{
                    method: 'POST',
                    headers: {{ 'X-Filename': encodeURIComponent(file.name) }},
                    body: file
                }});
                input.value = '';
            }} catch(e) {{
                console.error("Upload failed", e);
            }}
        }}

        function renderMessages(msgs) {{
            const container = document.getElementById('chat-container');
            msgs.forEach(m => {{
                if (document.getElementById('msg-' + m.id)) return;
                const isMine = (m.sender_id === clientId);
                const isSystem = (m.type === 'system');

                const row = document.createElement('div');
                row.id = 'msg-' + m.id;
                
                if (isSystem) {{
                    row.className = 'msg-system';
                    row.innerText = m.text;
                }} else {{
                    row.className = 'msg-row ' + (isMine ? 'mine' : 'other');
                    let contentHtml = escapeHtml(m.text);
                    if (m.type === 'file' && m.file) {{
                        contentHtml += `<div class="file-attach-card">
                            <span style="font-size:12px;overflow:hidden;text-overflow:ellipsis;">📁 ${{escapeHtml(m.file.filename)}}</span>
                            <a href="${{escapeHtml(m.file.url)}}" download class="file-attach-btn">دانلود</a>
                        </div>`;
                    }}
                    row.innerHTML = `
                        ${{!isMine ? `<div class="msg-sender" style="color:${{m.sender_color || '#38bdf8'}}">${{escapeHtml(m.sender_name)}}</div>` : ''}}
                        <div class="msg-bubble">
                            <div>${{contentHtml}}</div>
                            <div class="msg-meta">${{m.time}}</div>
                        </div>
                    `;
                }}
                container.appendChild(row);
            }});
            container.scrollTop = container.scrollHeight;
        }}

        function escapeHtml(str) {{
            if (!str) return '';
            const d = document.createElement('div');
            d.innerText = str;
            return d.innerHTML;
        }}

        // ── Polling & Signaling ──────────────────────────────────
        let pollTimer = null;
        function startPolling() {{
            if (pollTimer) clearInterval(pollTimer);
            pollTimer = setInterval(async () => {{
                if (!clientId) return;
                try {{
                    const res = await fetch(`/api/lan/chat/poll?room_id=${{ROOM_ID}}&client_id=${{clientId}}&last_msg_seq=${{lastMsgSeq}}&last_sig_seq=${{lastSigSeq}}`);
                    const data = await res.json();
                    if (data.messages && data.messages.length > 0) {{
                        renderMessages(data.messages);
                        lastMsgSeq = data.next_msg_seq;
                    }}
                    if (data.participants) {{
                        participants = data.participants;
                    }}
                    if (data.signals && data.signals.length > 0) {{
                        lastSigSeq = data.next_sig_seq;
                        data.signals.forEach(handleSignal);
                    }}
                }} catch(e) {{
                    console.error("Poll error", e);
                }}
            }}, 1200);
        }}

        // ── WebRTC Calling over LAN ──────────────────────────────
        const rtcConfig = {{ iceServers: [] }}; // Direct LAN p2p, zero external stun

        async function initiateCall(type) {{
            const other = participants.find(p => !p.is_self);
            if (!other) {{
                alert("کاربر دیگری در این اتاق آنلاین نیست!");
                return;
            }}
            activeCallWith = other.id;
            try {{
                localStream = await navigator.mediaDevices.getUserMedia({{
                    audio: true,
                    video: (type === 'video')
                }});
                document.getElementById('local-video').srcObject = localStream;
                document.getElementById('call-overlay').style.display = 'flex';
                document.getElementById('call-status').innerText = `در حال برقراری تماس با ${{other.name}}...`;

                setupPeerConnection();
                localStream.getTracks().forEach(track => peerConn.addTrack(track, localStream));

                const offer = await peerConn.createOffer();
                await peerConn.setLocalDescription(offer);

                sendSignal(activeCallWith, 'offer', {{ offer, callType: type, callerName: myName }});
            }} catch(err) {{
                alert("دسترسی به میکروفون/دوربین امکان‌پذیر نیست: " + err.message);
            }}
        }}

        function setupPeerConnection() {{
            peerConn = new RTCPeerConnection(rtcConfig);
            peerConn.onicecandidate = (event) => {{
                if (event.candidate && activeCallWith) {{
                    sendSignal(activeCallWith, 'ice-candidate', event.candidate);
                }}
            }};
            peerConn.ontrack = (event) => {{
                document.getElementById('remote-video').srcObject = event.streams[0];
                document.getElementById('call-status').innerText = 'تماس متصل است (LAN)';
            }};
        }}

        async function handleSignal(sig) {{
            const {{ from_id, type, data }} = sig;
            if (type === 'offer') {{
                pendingCall = {{ from_id, data }};
                document.getElementById('ring-caller-text').innerText = `${{data.callerName || 'کاربر'}} در حال برقراری تماس است...`;
                document.getElementById('modal-ring').style.display = 'flex';
            }} else if (type === 'answer' && peerConn) {{
                await peerConn.setRemoteDescription(new RTCSessionDescription(data.answer));
            }} else if (type === 'ice-candidate' && peerConn) {{
                try {{
                    await peerConn.addIceCandidate(new RTCIceCandidate(data));
                }} catch(e) {{}}
            }} else if (type === 'hangup') {{
                endCall(false);
            }} else if (type === 'reject') {{
                alert("تماس رد شد.");
                endCall(false);
            }}
        }}

        async function acceptCall() {{
            document.getElementById('modal-ring').style.display = 'none';
            if (!pendingCall) return;
            const {{ from_id, data }} = pendingCall;
            activeCallWith = from_id;

            try {{
                localStream = await navigator.mediaDevices.getUserMedia({{
                    audio: true,
                    video: (data.callType === 'video')
                }});
                document.getElementById('local-video').srcObject = localStream;
                document.getElementById('call-overlay').style.display = 'flex';
                document.getElementById('call-status').innerText = 'در حال اتصال...';

                setupPeerConnection();
                localStream.getTracks().forEach(track => peerConn.addTrack(track, localStream));

                await peerConn.setRemoteDescription(new RTCSessionDescription(data.offer));
                const answer = await peerConn.createAnswer();
                await peerConn.setLocalDescription(answer);

                sendSignal(activeCallWith, 'answer', {{ answer }});
            }} catch(err) {{
                alert("خطا در پاسخ به تماس: " + err.message);
                rejectCall();
            }}
        }}

        function rejectCall() {{
            document.getElementById('modal-ring').style.display = 'none';
            if (pendingCall) {{
                sendSignal(pendingCall.from_id, 'reject', {{}});
                pendingCall = null;
            }}
        }}

        function endCall(notify = true) {{
            if (notify && activeCallWith) {{
                sendSignal(activeCallWith, 'hangup', {{}});
            }}
            if (peerConn) {{ peerConn.close(); peerConn = null; }}
            if (localStream) {{
                localStream.getTracks().forEach(t => t.stop());
                localStream = null;
            }}
            document.getElementById('call-overlay').style.display = 'none';
            activeCallWith = null;
        }}

        function toggleMic() {{
            if (!localStream) return;
            const audioTrack = localStream.getAudioTracks()[0];
            if (audioTrack) {{
                audioTrack.enabled = !audioTrack.enabled;
                document.getElementById('btn-toggle-mic').classList.toggle('active', !audioTrack.enabled);
            }}
        }}

        async function sendSignal(toId, sigType, data) {{
            if (!clientId) return;
            await fetch('/api/lan/chat/signal', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ room_id: ROOM_ID, from_id: clientId, to_id: toId, type: sigType, data: data }})
            }});
        }}
    </script>
</body>
</html>
"""
