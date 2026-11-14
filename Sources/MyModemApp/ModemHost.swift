import Foundation

struct ModemHost: Sendable, Hashable {
    enum ValidationError: LocalizedError, Equatable {
        case empty
        case malformed
        case notPrivateLAN

        var errorDescription: String? {
            switch self {
            case .empty: "آدرس مودم خالی است."
            case .malformed: "فقط یک آدرس IPv4 ساده، بدون پروتکل، پورت یا مسیر وارد کنید."
            case .notPrivateLAN: "آدرس مودم باید داخل شبکهٔ خصوصی 10.x، 172.16–31.x یا 192.168.x باشد."
            }
        }
    }

    let value: String

    init(_ input: String) throws {
        let candidate = input.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !candidate.isEmpty else { throw ValidationError.empty }
        guard !candidate.contains("://"),
              !candidate.contains(":"),
              !candidate.contains("/"),
              !candidate.contains("?"),
              !candidate.contains("#")
        else { throw ValidationError.malformed }

        let components = candidate.split(separator: ".", omittingEmptySubsequences: false)
        guard components.count == 4 else { throw ValidationError.malformed }
        let octets = try components.map { part -> UInt8 in
            guard !part.isEmpty,
                  part.allSatisfy(\.isNumber),
                  (part.count == 1 || part.first != "0"),
                  let value = UInt8(part)
            else { throw ValidationError.malformed }
            return value
        }

        let isPrivate10 = octets[0] == 10
        let isPrivate172 = octets[0] == 172 && (16...31).contains(octets[1])
        let isPrivate192 = octets[0] == 192 && octets[1] == 168
        guard isPrivate10 || isPrivate172 || isPrivate192 else { throw ValidationError.notPrivateLAN }
        guard octets != [0, 0, 0, 0], octets != [255, 255, 255, 255] else { throw ValidationError.notPrivateLAN }
        value = candidate
    }
}
