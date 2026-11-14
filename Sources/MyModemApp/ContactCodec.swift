import Foundation

struct ContactCodec {
    struct ParsedContact: Sendable, Hashable {
        let name: String
        let number: String
        let group: ContactGroup
    }

    static func vCard(_ contacts: [ModemContact]) -> String {
        var lines = ["BEGIN:VCARD", "VERSION:3.0"]
        for contact in contacts where !contact.number.isEmpty {
            lines.append("BEGIN:VCARD")
            lines.append("VERSION:3.0")
            lines.append("FN:\(escape(contact.name))")
            lines.append("TEL;TYPE=CELL:\(contact.number)")
            lines.append("CATEGORIES:\(contact.records.first?.group.title ?? "عمومی")")
            lines.append("END:VCARD")
        }
        lines.append("END:VCARD")
        return lines.joined(separator: "\r\n") + "\r\n"
    }

    static func csv(_ contacts: [ModemContact]) -> String {
        var rows = ["name,number,group,storage"]
        for contact in contacts {
            let record = contact.records.first
            rows.append([
                quote(contact.name),
                quote(contact.number),
                quote(record?.group.title ?? "عمومی"),
                quote(record?.storage.title ?? "مودم")
            ].joined(separator: ","))
        }
        return rows.joined(separator: "\n") + "\n"
    }

    static func parse(_ text: String) -> [ParsedContact] {
        text.contains("BEGIN:VCARD") ? parseVCard(text) : parseCSV(text)
    }

    private static func parseVCard(_ text: String) -> [ParsedContact] {
        var results: [ParsedContact] = []
        var name = ""
        var number = ""
        var group = ContactGroup.common
        for rawLine in text.components(separatedBy: .newlines) {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            let upper = line.uppercased()
            if upper.hasPrefix("FN:") { name = String(line.dropFirst(3)).trimmingCharacters(in: .whitespaces) }
            else if upper.hasPrefix("TEL") {
                number = line.split(separator: ":", maxSplits: 1).last.map(String.init) ?? ""
            } else if upper.hasPrefix("CATEGORIES:") {
                group = groupFrom(String(line.dropFirst(11)))
            } else if upper == "END:VCARD" {
                if !number.isEmpty { results.append(.init(name: name.isEmpty ? number : name, number: number, group: group)) }
                name = ""; number = ""; group = .common
            }
        }
        return results
    }

    private static func parseCSV(_ text: String) -> [ParsedContact] {
        var results: [ParsedContact] = []
        for (index, rawLine) in text.components(separatedBy: .newlines).enumerated() {
            let line = rawLine.trimmingCharacters(in: .whitespaces)
            guard !line.isEmpty else { continue }
            let fields = line.split(separator: ",", omittingEmptySubsequences: false).map { unquote(String($0).trimmingCharacters(in: .whitespaces)) }
            if index == 1, fields.first?.lowercased() == "name" { continue }
            guard fields.count >= 2 else { continue }
            let name = fields[0]
            let number = fields[1]
            guard !number.isEmpty, number.contains(where: \.isNumber) else { continue }
            results.append(.init(name: name.isEmpty ? number : name, number: number, group: fields.count > 2 ? groupFrom(fields[2]) : .common))
        }
        return results
    }

    private static func groupFrom(_ value: String) -> ContactGroup {
        switch value.trimmingCharacters(in: .whitespaces) {
        case "خانواده", "family": .family
        case "دوستان", "friend": .friend
        case "همکاران", "colleague": .colleague
        default: .common
        }
    }

    private static func escape(_ value: String) -> String {
        value.replacingOccurrences(of: "\\", with: "\\\\").replacingOccurrences(of: ";", with: "\\;").replacingOccurrences(of: ",", with: "\\,")
    }

    private static func quote(_ value: String) -> String {
        "\"" + value.replacingOccurrences(of: "\"", with: "\"\"") + "\""
    }

    private static func unquote(_ value: String) -> String {
        guard value.hasPrefix("\""), value.hasSuffix("\""), value.count >= 2 else { return value }
        return String(value.dropFirst().dropLast()).replacingOccurrences(of: "\"\"", with: "\"")
    }
}
