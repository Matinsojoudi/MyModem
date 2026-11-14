@preconcurrency import Network
import AppKit
import CoreImage.CIFilterBuiltins
import Foundation
import Observation
import UniformTypeIdentifiers

@MainActor
@Observable
final class LANHub {
    enum State: Equatable { case stopped, starting, running, failed(String) }

    private(set) var state: State = .stopped
    private(set) var port: UInt16?
    private(set) var pairingCode: PairingCode?
    private(set) var uploadedByGuests = 0
    var expirationDays = 7

    let auth = LANAuth()
    let library = FileLibrary()
    let clipboard = ClipboardStore()

    private var listener: NWListener?
    private var connections: [ObjectIdentifier: HTTPConnection] = [:]

    var address: String { FileShareServer.preferredLANAddress() ?? "127.0.0.1" }
    var baseURL: URL? { port.map { URL(string: "http://\(address):\($0)")! } }

    func start() {
        guard listener == nil else { return }
        state = .starting
        do {
            let listener = try NWListener(using: .tcp, on: .any)
            self.listener = listener
            listener.newConnectionHandler = { [weak self] connection in
                Task { @MainActor in self?.accept(connection) }
            }
            listener.stateUpdateHandler = { [weak self] newState in
                Task { @MainActor in
                    guard let self else { return }
                    switch newState {
                    case .ready: self.port = listener.port?.rawValue; self.state = .running
                    case .failed(let error): self.state = .failed(error.localizedDescription); self.listener = nil
                    case .cancelled: if self.state != .stopped { self.state = .stopped }
                    default: break
                    }
                }
            }
            listener.start(queue: .global(qos: .userInitiated))
        } catch { state = .failed(error.localizedDescription) }
    }

    func stop() {
        listener?.cancel(); listener = nil
        connections.values.forEach { $0.cancel() }
        connections.removeAll()
        port = nil
        state = .stopped
        pairingCode = nil
    }

    func makePairingCode() { pairingCode = auth.beginPairing() }

    func cancelPairing() { auth.cancelPairing(); pairingCode = nil }

    func pairingURL() -> URL? {
        guard let code = pairingCode, let base = baseURL else { return nil }
        return URL(string: base.absoluteString + "/pair?c=" + code.code)
    }

    func qrImage(size: CGFloat = 190) -> NSImage? {
        guard let value = pairingURL()?.absoluteString.data(using: .utf8) else { return nil }
        let filter = CIFilter.qrCodeGenerator()
        filter.message = value
        filter.correctionLevel = "M"
        guard let output = filter.outputImage else { return nil }
        let scale = size / output.extent.width
        let representation = NSCIImageRep(ciImage: output.transformed(by: .init(scaleX: scale, y: scale)))
        let image = NSImage(size: representation.size)
        image.addRepresentation(representation)
        return image
    }

    func addFiles() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = true
        panel.canChooseDirectories = false
        panel.prompt = "افزودن به کتابخانه"
        guard panel.runModal() == .OK else { return }
        for url in panel.urls {
            let expiry = expirationDays > 0 ? Date().addingTimeInterval(TimeInterval(expirationDays * 86_400)) : nil
            _ = try? library.add(url: url, expiry: expiry)
        }
    }

    func copyURL(for file: LibraryFile) {
        guard let base = baseURL else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(base.absoluteString + "/f/" + file.id, forType: .string)
    }

    private func accept(_ connection: NWConnection) {
        let handler = HTTPConnection(connection: connection, hub: self)
        connections[ObjectIdentifier(handler)] = handler
        handler.onClose = { [weak self] in
            Task { @MainActor in self?.connections[ObjectIdentifier(handler)] = nil }
        }
        handler.start()
    }

    // MARK: - Request routing

    func respond(to request: HTTPRequest, on connection: NWConnection) {
        switch (request.method, request.path) {
        case ("GET", "/"): sendGuestPage(request, connection)
        case ("GET", "/pair"): handlePairGet(request, connection)
        case ("POST", "/api/pair"): handlePairPost(request, connection)
        case ("GET", "/api/files"): withAuth(request, connection) { [self] device in
            let list = library.files.map { ["id": $0.id, "name": $0.fileName, "size": String($0.size), "downloads": String($0.downloads)] }
            sendJSON(["files": list, "device": device.name], connection)
        }
        case ("GET", let path) where path.hasPrefix("/f/"):
            withAuth(request, connection) { [self] _ in
                let id = String(path.dropFirst(3))
                guard let file = library.files.first(where: { $0.id == id }), let url = library.url(for: file) else {
                    sendJSON(["error": "not found"], connection, status: "404 Not Found"); return
                }
                library.recordDownload(id)
                streamFile(file, url: url, request: request, connection: connection)
            }
        case ("POST", "/api/upload"): withAuth(request, connection) { [self] _ in
            guard let rawName = request.header("x-filename"),
                  let name = rawName.removingPercentEncoding, let body = request.body
            else { sendJSON(["error": "missing filename"], connection, status: "400 Bad Request"); return }
            do {
                let mime = UTType(filenameExtension: (name as NSString).pathExtension)?.preferredMIMEType ?? "application/octet-stream"
                let file = try library.importData(body, name: name, mime: mime)
                uploadedByGuests += 1
                sendJSON(["ok": true, "id": file.id, "size": String(file.size)], connection)
            } catch { sendJSON(["error": error.localizedDescription], connection, status: "413 Payload Too Large") }
        }
        case ("POST", "/api/delete"): withAuth(request, connection) { [self] _ in
            guard let id = request.json["id"] as? String, let file = library.files.first(where: { $0.id == id }) else {
                sendJSON(["error": "not found"], connection, status: "404 Not Found"); return
            }
            library.remove(file)
            sendJSON(["ok": true], connection)
        }
        case ("GET", "/api/clipboard"): withAuth(request, connection) { [self] _ in
            sendJSON(["text": clipboard.text, "updatedAt": clipboard.updatedAt.map { ISO8601DateFormatter().string(from: $0) } ?? ""], connection)
        }
        case ("POST", "/api/clipboard"): withAuth(request, connection) { [self] _ in
            guard let text = request.json["text"] as? String else { sendJSON(["error": "missing text"], connection, status: "400 Bad Request"); return }
            let complete = clipboard.update(text)
            sendJSON(["ok": complete], connection)
        }
        default: sendJSON(["error": "not found"], connection, status: "404 Not Found")
        }
    }

    private func withAuth(_ request: HTTPRequest, _ connection: NWConnection, action: (PairedDevice) -> Void) {
        guard let token = request.sessionToken, let device = auth.authorize(token: token) else {
            sendJSON(["error": "unauthorized"], connection, status: "401 Unauthorized"); return
        }
        action(device)
    }

    private func handlePairGet(_ request: HTTPRequest, _ connection: NWConnection) {
        guard let code = request.query["c"], let token = auth.redeem(code: code, deviceName: request.header("user-agent") ?? "دستگاه مهمان") else {
            sendHTML(pairPage(error: auth.activeCode == nil ? "کد منقضی شده است. کد تازه بسازید." : "کد نامعتبر است."), connection); return
        }
        pairingCode = nil
        var headers = "Set-Cookie: mm_session=\(token); Path=/; HttpOnly; SameSite=Lax\r\n"
        headers += "Location: /\r\n"
        sendResponse(status: "303 See Other", body: Data(), connection: connection, extraHeaders: headers)
    }

    private func handlePairPost(_ request: HTTPRequest, _ connection: NWConnection) {
        guard let code = request.json["code"] as? String,
              let token = auth.redeem(code: code, deviceName: request.json["name"] as? String ?? "دستگاه مهمان") else {
            sendJSON(["error": "pairing failed"], connection, status: "403 Forbidden"); return
        }
        pairingCode = nil
        sendJSON(["token": token], connection)
    }

    private func sendGuestPage(_ request: HTTPRequest, _ connection: NWConnection) {
        guard let token = request.sessionToken, auth.authorize(token: token) != nil else {
            sendResponse(status: "303 See Other", body: Data(), connection: connection, extraHeaders: "Location: /pair\r\n"); return
        }
        sendHTML(guestPage, connection)
    }

    private func streamFile(_ file: LibraryFile, url: URL, request: HTTPRequest, connection: NWConnection) {
        guard let handle = try? FileHandle(forReadingFrom: url) else {
            sendJSON(["error": "unreadable"], connection, status: "500 Server Error"); return
        }
        var start: Int64 = 0
        var end = file.size - 1
        var status = "200 OK"
        if let range = request.header("range"), let parsed = Self.parseRange(range, size: file.size) {
            start = parsed.lowerBound
            end = parsed.upperBound
            status = "206 Partial Content"
        }
        let length = end - start + 1
        try? handle.seek(toOffset: UInt64(start))
        let safe = FileLibrary.sanitizedName(file.fileName)
        var headers = "Content-Type: \(file.mime)\r\nContent-Length: \(length)\r\n"
        headers += "Content-Disposition: attachment; filename=\"\(safe)\"\r\n"
        headers += "Accept-Ranges: bytes\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n"
        if status == "206 Partial Content" { headers += "Content-Range: bytes \(start)-\(end)/\(file.size)\r\n" }
        sendResponse(status: status, body: Data(), connection: connection, extraHeaders: headers, contentLengthProvided: true, streaming: true) { [weak self] in
            self?.pump(handle: handle, remaining: length, connection: connection)
        }
    }

    private func pump(handle: FileHandle, remaining: Int64, connection: NWConnection) {
        guard remaining > 0 else { try? handle.close(); connection.cancel(); return }
        let chunk = (try? handle.read(upToCount: Int(min(remaining, 256 * 1024)))) ?? Data()
        guard !chunk.isEmpty else { try? handle.close(); connection.cancel(); return }
        let finished = Int64(chunk.count) >= remaining
        connection.send(content: chunk, contentContext: .defaultMessage, isComplete: finished, completion: .contentProcessed { [weak self] error in
            Task { @MainActor in
                guard error == nil else { try? handle.close(); connection.cancel(); return }
                if finished { try? handle.close(); connection.cancel(); return }
                self?.pump(handle: handle, remaining: remaining - Int64(chunk.count), connection: connection)
            }
        })
    }

    nonisolated static func parseRange(_ value: String, size: Int64) -> ClosedRange<Int64>? {
        guard value.lowercased().hasPrefix("bytes="), size > 0 else { return nil }
        let spec = value.dropFirst(6).split(separator: ",").first.map(String.init) ?? ""
        let parts = spec.split(separator: "-", omittingEmptySubsequences: false)
        guard parts.count == 2 else { return nil }
        if parts[0].isEmpty, let suffix = Int64(parts[1]), suffix > 0 {
            let length = min(suffix, size)
            return (size - length)...(size - 1)
        }
        guard let start = Int64(parts[0]), start >= 0, start < size else { return nil }
        let requestedEnd = parts[1].isEmpty ? size - 1 : (Int64(parts[1]) ?? size - 1)
        return start...min(max(requestedEnd, start), size - 1)
    }

    // MARK: - Responses

    func sendJSON(_ object: [String: Any], _ connection: NWConnection, status: String = "200 OK") {
        let data = (try? JSONSerialization.data(withJSONObject: object)) ?? Data("{}".utf8)
        sendResponse(status: status, body: data, connection: connection, extraHeaders: "Content-Type: application/json; charset=utf-8\r\n", contentTypeHeaderIncluded: true)
    }

    func sendHTML(_ html: String, _ connection: NWConnection) {
        sendResponse(status: "200 OK", body: Data(html.utf8), connection: connection, extraHeaders: "Content-Type: text/html; charset=utf-8\r\n", contentTypeHeaderIncluded: true)
    }

    func sendResponse(status: String, body: Data, connection: NWConnection, extraHeaders: String = "", contentTypeHeaderIncluded: Bool = false, contentLengthProvided: Bool = false, streaming: Bool = false, completion: (@MainActor @Sendable () -> Void)? = nil) {
        var head = "HTTP/1.1 \(status)\r\n"
        if !contentTypeHeaderIncluded { head += "Content-Type: text/plain; charset=utf-8\r\n" }
        if !contentLengthProvided { head += "Content-Length: \(body.count)\r\n" }
        head += extraHeaders
        head += "Connection: close\r\n\r\n"
        let context: NWConnection.ContentContext = streaming ? .defaultMessage : .finalMessage
        connection.send(content: Data(head.utf8) + body, contentContext: context, isComplete: !streaming, completion: .contentProcessed { [weak self] error in
            Task { @MainActor in
                guard error == nil else { connection.cancel(); return }
                if let completion { completion() } else { self?.closeSoon(connection) }
            }
        })
    }

    private func closeSoon(_ connection: NWConnection) { connection.cancel() }

    // MARK: - Guest UI

    private var guestPage: String {
        let rows = library.files.map { file in
            "<li><span>\(escape(file.fileName))</span><a href=\"/f/\(file.id)\">دانلود</a></li>"
        }.joined()
        return """
        <!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1">
        <title>MyModem — انتقال فایل</title><style>
        :root{--navy:#0A2342;--blue:#1464A5;--canvas:#EAF3FA;--ink:#0F253D;--muted:#587088}
        *{box-sizing:border-box}body{margin:0;font-family:-apple-system,system-ui,sans-serif;background:var(--canvas);color:var(--ink)}
        header{background:linear-gradient(135deg,var(--blue),var(--navy));color:#fff;padding:22px 20px}
        h1{font-size:18px;margin:0}main{padding:18px;display:grid;gap:16px}
        section{background:#fff;border-radius:16px;padding:16px;box-shadow:0 6px 20px rgba(10,35,66,.06)}
        ul{list-style:none;padding:0;margin:0;display:grid;gap:10px}
        li{display:flex;justify-content:space-between;align-items:center;gap:12px;padding:10px;border:1px solid #CDDEEB;border-radius:10px}
        a{color:var(--blue);font-weight:600;text-decoration:none}textarea{width:100%;min-height:90px;border:1px solid #CDDEEB;border-radius:10px;padding:10px;font:inherit}
        button{background:var(--blue);color:#fff;border:0;border-radius:999px;padding:10px 18px;font-weight:600}
        .muted{color:var(--muted);font-size:13px}
        </style></head><body><header><h1>MyModem — انتقال امن در شبکهٔ محلی</h1>
        <div class="muted" style="color:#cfe3f5">فایل‌ها از طریق Wi‑Fi مودم منتقل می‌شوند</div></header>
        <main>
        <section><h3>فایل‌های اشتراک‌گذاشته‌شده</h3><ul>\(rows.isEmpty ? "<li class=\"muted\">هنوز فایلی نیست</li>" : rows)</ul></section>
        <section><h3>ارسال فایل به مک</h3><input type="file" id="f"><button onclick="up()">آپلود</button><div id="u" class="muted"></div></section>
        <section><h3>کلیپ‌بورد مشترک</h3><textarea id="c"></textarea><button onclick="save()">ذخیره</button><button onclick="load()">بازخوانی</button></section>
        </main><script>
        async function up(){const f=document.getElementById('f').files[0];if(!f)return;
        document.getElementById('u').textContent='در حال ارسال…';
        const r=await fetch('/api/upload',{method:'POST',headers:{'X-Filename':encodeURIComponent(f.name)},body:f});
        document.getElementById('u').textContent=r.ok?'ارسال شد':'خطا';}
        async function save(){await fetch('/api/clipboard',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text:document.getElementById('c').value})});}
        async function load(){const r=await fetch('/api/clipboard');const j=await r.json();document.getElementById('c').value=j.text||'';}
        load();
        </script></body></html>
        """
    }

    private func pairPage(error: String?) -> String {
        """
        <!doctype html><html lang="fa" dir="rtl"><head><meta charset="utf-8">
        <meta name="viewport" content="width=device-width,initial-scale=1"><title>Pairing — MyModem</title>
        <style>body{font-family:-apple-system,system-ui,sans-serif;background:#0A2342;color:#fff;display:grid;place-items:center;min-height:100vh;margin:0}
        form{background:#fff;color:#0F253D;padding:24px;border-radius:18px;width:min(340px,88vw)}
        input{width:100%;font-size:22px;letter-spacing:8px;text-align:center;padding:10px;border:1px solid #CDDEEB;border-radius:10px;margin:14px 0}
        button{width:100%;padding:12px;border:0;border-radius:999px;background:#1464A5;color:#fff;font-weight:700}
        .err{color:#CA4747;font-size:13px}</style></head><body>
        <form method="get" action="/pair"><h2>اتصال دستگاه</h2>
        <p class="err">\(error ?? "")</p>
        <p>کد ۶ رقمی روی مک را وارد کنید</p>
        <input name="c" inputmode="numeric" maxlength="6" autofocus>
        <button type="submit">اتصال</button></form></body></html>
        """
    }

    private func escape(_ value: String) -> String {
        value.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "<", with: "&lt;").replacingOccurrences(of: ">", with: "&gt;")
    }
}

// MARK: - HTTP primitives

struct HTTPRequest {
    let method: String
    let path: String
    let query: [String: String]
    let headers: [String: String]
    let body: Data?
    let sessionToken: String?
    let json: [String: Any]

    func header(_ name: String) -> String? { headers[name.lowercased()] }

    init?(head: String, body: Data?) {
        let lines = head.components(separatedBy: "\r\n").filter { !$0.isEmpty }
        guard let requestLine = lines.first else { return nil }
        let parts = requestLine.split(separator: " ")
        guard parts.count >= 2 else { return nil }
        method = String(parts[0])
        let target = String(parts[1])
        let split = target.split(separator: "?", maxSplits: 1, omittingEmptySubsequences: false)
        path = String(split[0])
        var queryItems: [String: String] = [:]
        if split.count > 1 {
            for item in split[1].split(separator: "&") {
                let pair = item.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                if pair.count == 2 { queryItems[String(pair[0])] = String(pair[1]).removingPercentEncoding ?? String(pair[1]) }
            }
        }
        query = queryItems
        var parsed: [String: String] = [:]
        for line in lines.dropFirst() {
            guard let index = line.firstIndex(of: ":") else { continue }
            parsed[line[..<index].lowercased().trimmingCharacters(in: .whitespaces)] = line[line.index(after: index)...].trimmingCharacters(in: .whitespaces)
        }
        headers = parsed
        self.body = body
        var token: String?
        if let cookie = parsed["cookie"] {
            for part in cookie.split(separator: ";") {
                let pair = part.split(separator: "=", maxSplits: 1, omittingEmptySubsequences: false)
                if pair.count == 2, pair[0].trimmingCharacters(in: .whitespaces) == "mm_session" { token = String(pair[1]) }
            }
        }
        if let bearer = parsed["authorization"], bearer.lowercased().hasPrefix("bearer ") { token = String(bearer.dropFirst(7)) }
        sessionToken = token
        if let body, let object = try? JSONSerialization.jsonObject(with: body) as? [String: Any] { json = object } else { json = [:] }
    }
}

@MainActor
final class HTTPConnection {
    private let connection: NWConnection
    private weak var hub: LANHub?
    private var buffer = Data()
    private var pendingHead: String?
    private var expectedBody = 0
    var onClose: (() -> Void)?

    init(connection: NWConnection, hub: LANHub) {
        self.connection = connection
        self.hub = hub
    }

    func start() {
        connection.start(queue: .global(qos: .userInitiated))
        receive()
    }

    func cancel() { connection.cancel(); onClose?() }

    private func receive() {
        connection.receive(minimumIncompleteLength: 1, maximumLength: 64 * 1024) { [weak self] data, _, isComplete, error in
            Task { @MainActor in
                guard let self else { return }
                if let data, !data.isEmpty { self.buffer.append(data) }
                if error != nil { self.cancel(); return }
                if self.parseIfReady() { return }
                if isComplete { self.cancel(); return }
                self.receive()
            }
        }
    }

    private func parseIfReady() -> Bool {
        if pendingHead == nil {
            guard let range = buffer.range(of: Data("\r\n\r\n".utf8)) else {
                if buffer.count > 32 * 1024 { hub?.sendJSON(["error": "header too large"], connection); cancel(); return true }
                return false
            }
            let head = String(decoding: buffer[..<range.lowerBound], as: UTF8.self)
            buffer.removeSubrange(..<range.upperBound)
            let lengthLine = head.components(separatedBy: "\r\n").first { $0.lowercased().hasPrefix("content-length:") }
            expectedBody = Int(lengthLine?.split(separator: ":").last?.trimmingCharacters(in: .whitespaces) ?? "0") ?? 0
            if expectedBody < 0 || expectedBody > 2 * 1_024 * 1_024 * 1_024 {
                hub?.sendJSON(["error": "payload too large"], connection, status: "413 Payload Too Large")
                cancel()
                return true
            }
            pendingHead = head
        }
        guard let head = pendingHead, buffer.count >= expectedBody else { return false }
        let body = buffer.prefix(expectedBody)
        pendingHead = nil
        finish(head: head, body: Data(body))
        return true
    }

    private func finish(head: String, body: Data) {
        guard let hub, let request = HTTPRequest(head: head, body: body.isEmpty ? nil : body) else {
            cancel(); return
        }
        hub.respond(to: request, on: connection)
    }
}
