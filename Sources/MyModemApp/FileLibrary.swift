import Foundation
import Observation
import UniformTypeIdentifiers

struct LibraryFile: Identifiable, Codable, Sendable, Hashable {
    let id: String
    let fileName: String
    let storedName: String
    let size: Int64
    let mime: String
    let addedAt: Date
    var expiresAt: Date?
    var downloads: Int
}

@MainActor
@Observable
final class FileLibrary {
    enum LibraryError: LocalizedError {
        case tooLarge(Int64)
        case notRegularFile
        case noSpace

        var errorDescription: String? {
            switch self {
            case .tooLarge(let limit): "حجم فایل بیش از سقف \(ByteCountFormatter.string(fromByteCount: limit, countStyle: .file)) است."
            case .notRegularFile: "فقط فایل معمولی قابل افزودن است."
            case .noSpace: "فضای آزاد کافی برای این فایل وجود ندارد."
            }
        }
    }

    static let maxFileSize: Int64 = 2 * 1_024 * 1_024 * 1_024
    static let totalQuota: Int64 = 8 * 1_024 * 1_024 * 1_024

    private(set) var files: [LibraryFile] = []
    let directory: URL
    private let indexURL: URL
    private var scopedURLs: [String: URL] = [:]

    init(baseDirectory: URL? = nil) {
        let base = baseDirectory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appending(path: "MyModem", directoryHint: .isDirectory)
        directory = base.appending(path: "Files", directoryHint: .isDirectory)
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        indexURL = base.appending(path: "library.json")
        load()
        purgeExpired()
    }

    var totalSize: Int64 { files.reduce(0) { $0 + $1.size } }

    func add(url: URL, expiry: Date? = nil) throws -> LibraryFile {
        let access = url.startAccessingSecurityScopedResource()
        defer { if access { url.stopAccessingSecurityScopedResource() } }
        let values = try url.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey])
        guard values.isRegularFile == true else { throw LibraryError.notRegularFile }
        let size = Int64(values.fileSize ?? 0)
        guard size <= Self.maxFileSize else { throw LibraryError.tooLarge(Self.maxFileSize) }
        guard totalSize + size <= Self.totalQuota else { throw LibraryError.noSpace }
        let id = UUID().uuidString.lowercased()
        let stored = id + "-" + Self.sanitizedName(url.lastPathComponent)
        let destination = directory.appending(path: stored)
        try FileManager.default.copyItem(at: url, to: destination)
        let mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType ?? "application/octet-stream"
        let file = LibraryFile(id: id, fileName: url.lastPathComponent, storedName: stored, size: size, mime: mime, addedAt: Date(), expiresAt: expiry, downloads: 0)
        files.insert(file, at: 0)
        save()
        return file
    }

    func addCopied(from source: URL) throws -> LibraryFile {
        try add(url: source)
    }

    func importData(_ data: Data, name: String, mime: String, expiry: Date? = nil) throws -> LibraryFile {
        let size = Int64(data.count)
        guard size <= Self.maxFileSize else { throw LibraryError.tooLarge(Self.maxFileSize) }
        guard totalSize + size <= Self.totalQuota else { throw LibraryError.noSpace }
        let id = UUID().uuidString.lowercased()
        let stored = id + "-" + Self.sanitizedName(name)
        try data.write(to: directory.appending(path: stored), options: .atomic)
        let file = LibraryFile(id: id, fileName: name, storedName: stored, size: size, mime: mime, addedAt: Date(), expiresAt: expiry, downloads: 0)
        files.insert(file, at: 0)
        save()
        return file
    }

    func remove(_ file: LibraryFile) {
        try? FileManager.default.removeItem(at: directory.appending(path: file.storedName))
        files.removeAll { $0.id == file.id }
        scopedURLs[file.id] = nil
        save()
    }

    func removeAll() {
        for file in files { try? FileManager.default.removeItem(at: directory.appending(path: file.storedName)) }
        files.removeAll()
        save()
    }

    func url(for file: LibraryFile) -> URL? {
        let candidate = directory.appending(path: file.storedName)
        guard candidate.standardizedFileURL.path.hasPrefix(directory.standardizedFileURL.path) else { return nil }
        return FileManager.default.fileExists(atPath: candidate.path) ? candidate : nil
    }

    func recordDownload(_ id: String) {
        guard let index = files.firstIndex(where: { $0.id == id }) else { return }
        files[index].downloads += 1
        save()
    }

    func purgeExpired() {
        let expired = files.filter { $0.expiresAt.map { Date() >= $0 } ?? false }
        guard !expired.isEmpty else { return }
        for file in expired { try? FileManager.default.removeItem(at: directory.appending(path: file.storedName)) }
        files.removeAll { $0.expiresAt.map { Date() >= $0 } ?? false }
        save()
    }

    private func load() {
        guard let data = try? Data(contentsOf: indexURL),
              let values = try? JSONDecoder().decode([LibraryFile].self, from: data) else { return }
        files = values.filter { FileManager.default.fileExists(atPath: directory.appending(path: $0.storedName).path) }
    }

    private func save() {
        if let data = try? JSONEncoder().encode(files) {
            try? data.write(to: indexURL, options: .atomic)
        }
    }

    nonisolated static func sanitizedName(_ value: String) -> String {
        let allowed = CharacterSet.alphanumerics.union(CharacterSet(charactersIn: "._-"))
        let scalars = value.unicodeScalars.map { allowed.contains($0) ? Character($0) : "_" }
        let cleaned = String(scalars).prefix(80)
        return cleaned.isEmpty ? "file" : String(cleaned)
    }
}

@MainActor
@Observable
final class ClipboardStore {
    static let maxLength = 64 * 1024
    private(set) var text = ""
    private(set) var updatedAt: Date?
    private let storeURL: URL

    init(baseDirectory: URL? = nil) {
        let base = baseDirectory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appending(path: "MyModem", directoryHint: .isDirectory)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        storeURL = base.appending(path: "clipboard.json")
        if let data = try? Data(contentsOf: storeURL),
           let value = try? JSONDecoder().decode([String: String].self, from: data) {
            text = value["text"] ?? ""
            updatedAt = value["updatedAt"].flatMap { ISO8601DateFormatter().date(from: $0) }
        }
    }

    @discardableResult
    func update(_ value: String) -> Bool {
        let trimmed = String(value.prefix(Self.maxLength))
        text = trimmed
        updatedAt = Date()
        let payload = ["text": trimmed, "updatedAt": ISO8601DateFormatter().string(from: Date())]
        if let data = try? JSONEncoder().encode(payload) { try? data.write(to: storeURL, options: .atomic) }
        return trimmed.count == value.count
    }

    func clear() {
        text = ""
        updatedAt = Date()
        try? FileManager.default.removeItem(at: storeURL)
    }
}
