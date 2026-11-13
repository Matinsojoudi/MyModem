@preconcurrency import Network
import AppKit
import CoreImage.CIFilterBuiltins
import Darwin
import Foundation
import Observation
import UniformTypeIdentifiers

struct SharedFile: Sendable, Equatable {
    let url: URL
    let name: String
    let size: Int64
    let contentType: String
    let token: String
    let expiresAt: Date
}

@MainActor
@Observable
final class FileShareServer {
    enum State: Equatable { case stopped, starting, running, failed(String) }

    private(set) var state: State = .stopped
    private(set) var sharedFile: SharedFile?
    private(set) var port: UInt16?
    private(set) var downloadCount = 0
    private(set) var lastDownloadAt: Date?
    var expirationMinutes = 60

    private var listener: NWListener?
    private var securityScopedURL: URL?

    var localAddress: String { Self.preferredLANAddress() ?? "127.0.0.1" }
    var downloadURL: URL? {
        guard let file = sharedFile, let port else { return nil }
        return URL(string: "http://\(localAddress):\(port)/d/\(file.token)")
    }

    func chooseFile() {
        let panel = NSOpenPanel()
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = false
        panel.prompt = "اشتراک‌گذاری"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        share(url: url)
    }

    func share(url: URL) {
        stop()
        let access = url.startAccessingSecurityScopedResource()
        do {
            let values = try url.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey, .contentTypeKey])
            guard values.isRegularFile == true else { throw FileShareError.notRegularFile }
            let token = Self.randomToken()
            let type = values.contentType?.preferredMIMEType ?? "application/octet-stream"
            sharedFile = SharedFile(url: url, name: url.lastPathComponent, size: Int64(values.fileSize ?? 0), contentType: type, token: token, expiresAt: Date().addingTimeInterval(TimeInterval(expirationMinutes * 60)))
            if access { securityScopedURL = url }
            try startListener()
        } catch {
            if access { url.stopAccessingSecurityScopedResource() }
            state = .failed(error.localizedDescription)
        }
    }

    func stop() {
        listener?.cancel()
        listener = nil
        securityScopedURL?.stopAccessingSecurityScopedResource()
        securityScopedURL = nil
        sharedFile = nil
        port = nil
        state = .stopped
        downloadCount = 0
        lastDownloadAt = nil
    }

    func copyLink() {
        guard let value = downloadURL?.absoluteString else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(value, forType: .string)
    }

    func qrImage(size: CGFloat = 220) -> NSImage? {
        guard let data = downloadURL?.absoluteString.data(using: .utf8) else { return nil }
        let filter = CIFilter.qrCodeGenerator()
        filter.message = data
        filter.correctionLevel = "M"
        guard let output = filter.outputImage else { return nil }
        let scale = size / output.extent.width
        let transformed = output.transformed(by: .init(scaleX: scale, y: scale))
        let representation = NSCIImageRep(ciImage: transformed)
        let image = NSImage(size: representation.size)
        image.addRepresentation(representation)
        return image
    }

    private func startListener() throws {
        state = .starting
        let listener = try NWListener(using: .tcp, on: .any)
        self.listener = listener
        listener.newConnectionHandler = { [weak self] connection in
            Task { @MainActor in self?.accept(connection) }
        }
        listener.stateUpdateHandler = { [weak self] newState in
            Task { @MainActor in
                guard let self else { return }
                switch newState {
                case .ready:
                    self.port = listener.port?.rawValue
                    self.state = .running
                case .failed(let error):
                    self.state = .failed(error.localizedDescription)
                    self.listener = nil
                case .cancelled:
                    if self.state != .stopped { self.state = .stopped }
                default: break
                }
            }
        }
        listener.start(queue: .global(qos: .userInitiated))
    }

    private func accept(_ connection: NWConnection) {
        connection.start(queue: .global(qos: .userInitiated))
        connection.receive(minimumIncompleteLength: 1, maximumLength: 16_384) { [weak self] data, _, _, error in
            Task { @MainActor in
                guard let self, error == nil, let data, let request = String(data: data, encoding: .utf8) else {
                    connection.cancel(); return
                }
                self.handle(request, connection: connection)
            }
        }
    }

    private func handle(_ request: String, connection: NWConnection) {
        guard let line = request.split(separator: "\r\n", maxSplits: 1).first else { respond(status: "400 Bad Request", body: "Bad request", connection: connection); return }
        let parts = line.split(separator: " ")
        guard parts.count >= 2 else { respond(status: "400 Bad Request", body: "Bad request", connection: connection); return }
        let method = String(parts[0])
        guard method == "GET" || method == "HEAD" else { respond(status: "405 Method Not Allowed", body: "Method not allowed", connection: connection, extra: "Allow: GET, HEAD\r\n"); return }
        guard let file = sharedFile, Date() < file.expiresAt else { respond(status: "410 Gone", body: "Share expired", connection: connection); stopExpiredShare(); return }
        let path = String(parts[1]).split(separator: "?", maxSplits: 1).first.map(String.init) ?? ""
        guard path.hasPrefix("/d/"), Self.constantTimeEquals(String(path.dropFirst(3)), file.token) else { respond(status: "404 Not Found", body: "Not found", connection: connection); return }
        send(file: file, headOnly: method == "HEAD", connection: connection)
    }

    private func send(file: SharedFile, headOnly: Bool, connection: NWConnection) {
        let encodedName = file.name.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? "download"
        let safeFallback = file.name.unicodeScalars.map { $0.isASCII && ($0.properties.isAlphabetic || CharacterSet.decimalDigits.contains($0)) ? Character(String($0)) : "_" }
        let fallback = String(safeFallback).replacingOccurrences(of: "\"", with: "_")
        let headers = "HTTP/1.1 200 OK\r\nContent-Type: \(file.contentType)\r\nContent-Length: \(file.size)\r\nContent-Disposition: attachment; filename=\"\(fallback)\"; filename*=UTF-8''\(encodedName)\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n"
        connection.send(content: Data(headers.utf8), completion: .contentProcessed { [weak self] error in
            guard error == nil else { connection.cancel(); return }
            if headOnly { connection.cancel(); return }
            Task { @MainActor in self?.stream(file: file, connection: connection) }
        })
    }

    private func stream(file: SharedFile, connection: NWConnection) {
        do {
            let handle = try FileHandle(forReadingFrom: file.url)
            streamChunk(handle: handle, connection: connection)
        } catch { connection.cancel() }
    }

    private func streamChunk(handle: FileHandle, connection: NWConnection) {
        do {
            let chunk = try handle.read(upToCount: 128 * 1024) ?? Data()
            guard !chunk.isEmpty else {
                try? handle.close()
                downloadCount += 1
                lastDownloadAt = Date()
                connection.cancel()
                return
            }
            connection.send(content: chunk, completion: .contentProcessed { [weak self] error in
                Task { @MainActor in
                    guard let self, error == nil else { try? handle.close(); connection.cancel(); return }
                    self.streamChunk(handle: handle, connection: connection)
                }
            })
        } catch {
            try? handle.close()
            connection.cancel()
        }
    }

    private func respond(status: String, body: String, connection: NWConnection, extra: String = "") {
        let data = Data(body.utf8)
        let response = "HTTP/1.1 \(status)\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: \(data.count)\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\(extra)Connection: close\r\n\r\n"
        connection.send(content: Data(response.utf8) + data, completion: .contentProcessed { _ in connection.cancel() })
    }

    private func stopExpiredShare() {
        listener?.cancel(); listener = nil
        securityScopedURL?.stopAccessingSecurityScopedResource(); securityScopedURL = nil
        state = .stopped; port = nil; sharedFile = nil
    }

    nonisolated static func constantTimeEquals(_ input: String, _ expected: String) -> Bool {
        let lhs = Array(input.utf8), rhs = Array(expected.utf8)
        var difference = UInt8(truncatingIfNeeded: lhs.count ^ rhs.count)
        for index in 0..<max(lhs.count, rhs.count) {
            difference |= (index < lhs.count ? lhs[index] : 0) ^ (index < rhs.count ? rhs[index] : 0)
        }
        return difference == 0
    }

    nonisolated static func randomToken() -> String {
        var bytes = [UInt8](repeating: 0, count: 16)
        let status = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return status == errSecSuccess ? bytes.map { String(format: "%02x", $0) }.joined() : UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased()
    }

    static func preferredLANAddress() -> String? {
        var pointer: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&pointer) == 0, let first = pointer else { return nil }
        defer { freeifaddrs(pointer) }
        var cursor: UnsafeMutablePointer<ifaddrs>? = first
        var fallback: String?
        while let current = cursor {
            defer { cursor = current.pointee.ifa_next }
            guard current.pointee.ifa_addr.pointee.sa_family == UInt8(AF_INET) else { continue }
            let name = String(cString: current.pointee.ifa_name)
            guard name != "lo0" else { continue }
            var address = current.pointee.ifa_addr.pointee
            var host = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            guard getnameinfo(&address, socklen_t(current.pointee.ifa_addr.pointee.sa_len), &host, socklen_t(host.count), nil, 0, NI_NUMERICHOST) == 0 else { continue }
            let bytes = host.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }
            let value = String(decoding: bytes, as: UTF8.self)
            if name == "en0" { return value }
            fallback = fallback ?? value
        }
        return fallback
    }
}

enum FileShareError: LocalizedError {
    case notRegularFile
    var errorDescription: String? { "فقط فایل معمولی قابل اشتراک‌گذاری است." }
}
