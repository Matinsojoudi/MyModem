import Foundation

struct ModemCodec: Sendable {
    func encode(_ text: String) -> String {
        text.replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .utf16
            .map { String(format: "%04X", $0) }
            .joined()
    }

    func decode(_ input: String) -> String {
        var value = input.trimmingCharacters(in: .whitespacesAndNewlines)
        for _ in 0..<3 {
            let compact = value.replacingOccurrences(of: " ", with: "")
            guard compact.count >= 4,
                  compact.count.isMultiple(of: 4),
                  compact.allSatisfy(\.isHexDigit),
                  let decoded = decodeUTF16BE(compact),
                  decoded.unicodeScalars.allSatisfy({ $0.value >= 32 || "\n\r\t".unicodeScalars.contains($0) })
            else { break }
            value = decoded.trimmingCharacters(in: .whitespacesAndNewlines)
        }

        return value
            .replacingOccurrences(of: "ك", with: "ک")
            .replacingOccurrences(of: "ي", with: "ی")
            .replacingOccurrences(of: "ى", with: "ی")
            .replacingOccurrences(of: "ئ", with: "ی")
            .replacingOccurrences(of: "\r\n", with: "\n")
            .replacingOccurrences(of: "\r", with: "\n")
            .trimmingCharacters(in: .whitespacesAndNewlines)
    }

    func normalizePhone(_ input: String) -> String {
        let translated = String(input.map { character in
            let persian = "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩"
            let ascii = "01234567890123456789"
            guard let index = persian.firstIndex(of: character) else { return character }
            let offset = persian.distance(from: persian.startIndex, to: index)
            return ascii[ascii.index(ascii.startIndex, offsetBy: offset)]
        })
        let allowed = translated.filter(\.isNumber)
        if allowed.hasPrefix("0098") { return "0" + allowed.dropFirst(4) }
        if allowed.hasPrefix("98"), allowed.count >= 12 { return "0" + allowed.dropFirst(2) }
        if allowed.hasPrefix("9"), allowed.count == 10 { return "0" + allowed }
        return allowed
    }

    private func decodeUTF16BE(_ hex: String) -> String? {
        var units: [UInt16] = []
        var index = hex.startIndex
        while index < hex.endIndex {
            guard let end = hex.index(index, offsetBy: 4, limitedBy: hex.endIndex),
                  let unit = UInt16(hex[index..<end], radix: 16)
            else { return nil }
            units.append(unit)
            index = end
        }
        return String(decoding: units, as: UTF16.self)
    }
}

struct JalaliDateFormatter: Sendable {
    private let months = ["", "فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور", "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]

    func string(fromModemTimestamp timestamp: String) -> String {
        let values = timestamp.split(separator: ",").compactMap { Int($0.trimmingCharacters(in: .whitespaces)) }
        guard values.count >= 6 else { return timestamp.isEmpty ? "--" : timestamp }
        let result = jalali(year: 2000 + values[0], month: values[1], day: values[2])
        guard months.indices.contains(result.month) else { return timestamp }
        return "\(result.day) \(months[result.month]) \(result.year) - ساعت \(String(format: "%02d:%02d", values[3], values[4]))"
    }

    private func jalali(year inputYear: Int, month: Int, day: Int) -> (year: Int, month: Int, day: Int) {
        let offsets = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
        var year = inputYear
        var jalaliYear: Int
        if year > 1600 { jalaliYear = 979; year -= 1600 } else { jalaliYear = 0; year -= 621 }
        let adjusted = month > 2 ? year : year - 1
        var days = 365 * year + (adjusted + 3) / 4 - (adjusted + 99) / 100 + (adjusted + 399) / 400 - 80 + day + offsets[month - 1]
        jalaliYear += 33 * (days / 12_053)
        days %= 12_053
        jalaliYear += 4 * (days / 1_461)
        days %= 1_461
        if days > 365 { jalaliYear += (days - 1) / 365; days = (days - 1) % 365 }
        if days < 186 { return (jalaliYear, 1 + days / 31, 1 + days % 31) }
        return (jalaliYear, 7 + (days - 186) / 30, 1 + (days - 186) % 30)
    }
}
