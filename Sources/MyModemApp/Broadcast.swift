import Foundation
import Observation

struct RecipientRow: Identifiable, Sendable, Hashable {
    let id: Int
    let raw: [String: String]
    let phone: String
    let displayName: String
}

struct RecipientList: Sendable {
    let headers: [String]
    let rows: [RecipientRow]
    let phoneColumn: String
}

enum BroadcastError: LocalizedError {
    case unreadable
    case emptyFile
    case noHeader
    case noPhoneColumn
    case noRows
    case tooMany(Int)

    var errorDescription: String? {
        switch self {
        case .unreadable: "فایل قابل خواندن نیست. UTF-8 یا Windows-1256 را بررسی کنید."
        case .emptyFile: "فایل خالی است."
        case .noHeader: "ردیف عنوان (header) پیدا نشد."
        case .noPhoneColumn: "ستون موبایل پیدا نشد. یکی از ستون‌ها باید «موبایل»، «mobile» یا «phone» باشد."
        case .noRows: "هیچ شمارهٔ معتبری در فایل نیست."
        case .tooMany(let limit): "تعداد ردیف‌ها بیش از سقف \(limit) است."
        }
    }
}

struct RecipientParser {
    static let maxRows = 500
    static let phoneAliases = ["موبایل", "همراه", "شماره موبایل", "mobile", "phone", "tel", "msisdn"]
    static let blockedHeaders = ["شماره دانشجویی", "student id", "studentid"]

    static func parse(data: Data) throws -> RecipientList {
        guard !data.isEmpty else { throw BroadcastError.emptyFile }
        guard let text = decode(data) else { throw BroadcastError.unreadable }
        let table = parseTable(text)
        guard let headers = table.first, headers.contains(where: { !$0.trimmingCharacters(in: .whitespaces).isEmpty }) else {
            throw BroadcastError.noHeader
        }
        let cleanHeaders = headers.map { $0.trimmingCharacters(in: .whitespaces).replacingOccurrences(of: "\u{FEFF}", with: "") }
        guard let phoneIndex = cleanHeaders.firstIndex(where: { header in
            let value = header.lowercased()
            return phoneAliases.contains { value.contains($0.lowercased()) } && !blockedHeaders.contains { value.contains($0) }
        }) else { throw BroadcastError.noPhoneColumn }

        let codec = ModemCodec()
        var rows: [RecipientRow] = []
        var seen = Set<String>()
        for (offset, fields) in table.dropFirst().enumerated() {
            guard phoneIndex < fields.count else { continue }
            let phone = codec.normalizePhone(fields[phoneIndex])
            guard !phone.isEmpty, !seen.contains(phone) else { continue }
            seen.insert(phone)
            var values: [String: String] = [:]
            for (index, header) in cleanHeaders.enumerated() where index < fields.count {
                values[header] = fields[index].trimmingCharacters(in: .whitespacesAndNewlines)
            }
            let first = values["نام"] ?? ""
            let last = values["نام‌خانوادگی"] ?? values["نام خانوادگی"] ?? values["فامیل"] ?? ""
            let full = [first, last].filter { !$0.isEmpty }.joined(separator: " ")
            values["نام کامل"] = full.isEmpty ? phone : full
            values["موبایل"] = phone
            rows.append(RecipientRow(id: offset, raw: values, phone: phone, displayName: full.isEmpty ? phone : full))
            if rows.count > maxRows { throw BroadcastError.tooMany(maxRows) }
        }
        guard !rows.isEmpty else { throw BroadcastError.noRows }
        return RecipientList(headers: cleanHeaders, rows: rows, phoneColumn: cleanHeaders[phoneIndex])
    }

    static func parse(url: URL) throws -> RecipientList {
        let access = url.startAccessingSecurityScopedResource()
        defer { if access { url.stopAccessingSecurityScopedResource() } }
        return try parse(data: try Data(contentsOf: url))
    }

    static func decode(_ data: Data) -> String? {
        if let utf8 = String(data: data, encoding: .utf8) {
            return utf8.hasPrefix("\u{FEFF}") ? String(utf8.dropFirst()) : utf8
        }
        let windowsArabic = String.Encoding(rawValue: CFStringConvertEncodingToNSStringEncoding(CFStringEncoding(CFStringEncodings.windowsArabic.rawValue)))
        return String(data: data, encoding: windowsArabic)
    }

    /// RFC-4180 style parser: handles quotes, embedded commas, doubled quotes and CRLF.
    static func parseTable(_ source: String) -> [[String]] {
        // Swift treats "\r\n" as one grapheme cluster, so normalize line endings first.
        let text = source
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
        var rows: [[String]] = []
        var row: [String] = []
        var field = ""
        var inQuotes = false
        var index = text.startIndex
        while index < text.endIndex {
            let character = text[index]
            if inQuotes {
                if character == "\"" {
                    let next = text.index(after: index)
                    if next < text.endIndex, text[next] == "\"" {
                        field.append("\"")
                        index = next
                    } else {
                        inQuotes = false
                    }
                } else {
                    field.append(character)
                }
            } else {
                switch character {
                case "\"": inQuotes = true
                case ",": row.append(field); field = ""
                case "\n":
                    row.append(field); field = ""
                    if !row.allSatisfy({ $0.trimmingCharacters(in: .whitespaces).isEmpty }) { rows.append(row) }
                    row = []
                case "\r": break
                default: field.append(character)
                }
            }
            index = text.index(after: index)
        }
        if !field.isEmpty || !row.isEmpty {
            row.append(field)
            if !row.allSatisfy({ $0.trimmingCharacters(in: .whitespaces).isEmpty }) { rows.append(row) }
        }
        return rows
    }
}

struct TemplateRenderer {
    static func variables(in template: String) -> [String] {
        matches(template).map(\.1)
    }

    static func render(_ template: String, with values: [String: String]) -> String {
        var result = template
        for (range, key) in matches(template).reversed() {
            result.replaceSubrange(range, with: values[key] ?? "")
        }
        return result
    }

    static func preview(_ template: String, row: RecipientRow? = nil, limit: Int = 160) -> String {
        let rendered = row.map { render(template, with: $0.raw) } ?? template
        return String(rendered.prefix(limit))
    }

    private static func matches(_ template: String) -> [(Range<String.Index>, String)] {
        var found: [(Range<String.Index>, String)] = []
        var searchStart = template.startIndex
        while let open = template.range(of: "{{", range: searchStart..<template.endIndex),
              let close = template.range(of: "}}", range: open.upperBound..<template.endIndex) {
            let key = String(template[open.upperBound..<close.lowerBound]).trimmingCharacters(in: .whitespaces)
            if !key.isEmpty { found.append((open.lowerBound..<close.upperBound, key)) }
            searchStart = close.upperBound
        }
        return found
    }
}

@MainActor
@Observable
final class BroadcastEngine {
    enum Phase: Equatable { case idle, running, paused, finished, stopped }

    private(set) var phase: Phase = .idle
    private(set) var list: RecipientList?
    private(set) var sent = 0
    private(set) var failed = 0
    private(set) var processed = 0
    private(set) var report: [RowResult] = []
    private(set) var lastError: String?

    var template = ""
    var delaySeconds = 2.0
    var minimumDelaySeconds = 1.5

    struct RowResult: Identifiable, Sendable, Hashable {
        let id: Int
        let name: String
        let phone: String
        var status: String
    }

    private var task: Task<Void, Never>?
    private var stopRequested = false

    var total: Int { list?.rows.count ?? 0 }
    var isRunning: Bool { phase == .running }
    var progress: Double { total == 0 ? 0 : Double(processed) / Double(total) }
    var missingVariables: [String] {
        guard let list, !template.isEmpty else { return [] }
        let available = Set(list.headers + ["نام کامل", "موبایل"])
        return Array(Set(TemplateRenderer.variables(in: template)).subtracting(available)).sorted()
    }

    func load(url: URL) {
        do {
            let parsed = try RecipientParser.parse(url: url)
            list = parsed
            report = parsed.rows.map { RowResult(id: $0.id, name: $0.displayName, phone: $0.phone, status: "در انتظار") }
            processed = 0; sent = 0; failed = 0
            phase = .idle
            lastError = nil
        } catch { lastError = error.localizedDescription }
    }

    func start(sender: @escaping @Sendable (String, String) async throws -> Void) {
        guard let list, !list.rows.isEmpty, !isRunning else { return }
        stopRequested = false
        phase = .running
        lastError = nil
        report = list.rows.map { RowResult(id: $0.id, name: $0.displayName, phone: $0.phone, status: "در انتظار") }

        task = Task { [weak self] in
            guard let self else { return }
            for (index, row) in list.rows.enumerated() {
                if self.stopRequested { break }
                let text = TemplateRenderer.render(self.template, with: row.raw)
                if text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                    self.report[index].status = "رد شد (متن خالی)"
                    self.failed += 1
                } else {
                    do {
                        try await sender(row.phone, text)
                        self.report[index].status = "ارسال شد"
                        self.sent += 1
                    } catch {
                        self.report[index].status = "ناموفق"
                        self.failed += 1
                        self.lastError = error.localizedDescription
                    }
                }
                self.processed += 1
                if index < list.rows.count - 1, !self.stopRequested {
                    try? await Task.sleep(for: .seconds(max(self.delaySeconds, self.minimumDelaySeconds)))
                }
            }
            self.phase = self.stopRequested ? .stopped : .finished
        }
    }

    func stop() {
        stopRequested = true
        task?.cancel()
        task = nil
        if phase == .running { phase = .stopped }
    }

    func reset() {
        stop()
        list = nil
        report = []
        processed = 0; sent = 0; failed = 0
        phase = .idle
        lastError = nil
    }

    func reportCSV() -> String {
        var lines = ["name,phone,status"]
        for row in report {
            lines.append([row.name, row.phone, row.status].map { "\"\($0.replacingOccurrences(of: "\"", with: "\"\""))\"" }.joined(separator: ","))
        }
        return lines.joined(separator: "\n") + "\n"
    }
}
