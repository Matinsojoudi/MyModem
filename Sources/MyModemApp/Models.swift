import Foundation

struct ModemStatus: Sendable {
    let batteryPercent: Int
    let isCharging: Bool
    let signalQuality: Int
    let connectedClients: Int
    let unreadMessages: Int
    let downloadSpeed: Int64
    let uploadSpeed: Int64
    let receivedBytes: Int64
    let sentBytes: Int64
    let uptimeSeconds: Int

    init(json: [String: Any]) {
        batteryPercent = Self.int(json["battery_percent"])
        isCharging = String(describing: json["battery_charging"] ?? "0") == "1"
        signalQuality = Self.int(json["signal_quality"])
        connectedClients = Self.int(json["wifi_clients_num"])
        unreadMessages = Self.int(json["unread_long"])
        downloadSpeed = Self.int64(json["rx_speed"])
        uploadSpeed = Self.int64(json["tx_speed"])
        receivedBytes = Self.int64(json["rx_byte_all"])
        sentBytes = Self.int64(json["tx_byte_all"])
        uptimeSeconds = Self.int(json["run_seconds"])
    }

    private static func int(_ value: Any?) -> Int {
        Int(String(describing: value ?? "0")) ?? 0
    }

    private static func int64(_ value: Any?) -> Int64 {
        Int64(String(describing: value ?? "0")) ?? 0
    }
}

enum ContactExportFormat: Sendable { case vcard, csv }

enum MessageDirection: String, Sendable, Hashable { case incoming, outgoing }

struct SMSMessage: Identifiable, Sendable, Hashable {
    let id: String
    let sender: String
    let senderName: String
    let text: String
    let rawTime: String
    let displayTime: String
    let isUnread: Bool
    let isMissedCall: Bool
    let callerNumber: String
    let storage: String
    let direction: MessageDirection

    var displaySender: String { senderName.isEmpty ? sender : senderName }
}

struct Conversation: Identifiable, Sendable, Hashable {
    let peerNumber: String
    let displayName: String
    let messages: [SMSMessage]
    var id: String { peerNumber }
    var lastMessage: SMSMessage? { messages.last }
    var unreadCount: Int { messages.filter { $0.direction == .incoming && $0.isUnread }.count }
}

enum ContactStorage: String, Sendable, Hashable, CaseIterable, Identifiable {
    case modem = "1"
    case sim = "0"
    var id: String { rawValue }
    var title: String { self == .sim ? "سیم‌کارت" : "حافظه مودم" }
}

enum ContactGroup: String, Sendable, Hashable, CaseIterable, Identifiable {
    case common, family, friend, colleague
    var id: String { rawValue }
    var title: String {
        switch self { case .common: "عمومی"; case .family: "خانواده"; case .friend: "دوستان"; case .colleague: "همکاران" }
    }
}

struct ContactRecord: Identifiable, Sendable, Hashable {
    let id: String
    let name: String
    let number: String
    let normalizedNumber: String
    let group: ContactGroup
    let storage: ContactStorage
}

struct ModemContact: Identifiable, Sendable, Hashable {
    let normalizedNumber: String
    let preferredName: String
    let records: [ContactRecord]

    var id: String { normalizedNumber.isEmpty ? records.map(\.id).joined(separator: "-") : normalizedNumber }
    var allIDs: [String] { records.map(\.id) }
    var name: String { preferredName }
    var number: String { records.first?.number ?? normalizedNumber }
    var group: String { records.first?.group.title ?? ContactGroup.common.title }
    var storage: String { Set(records.map(\.storage)).count > 1 ? "سیم‌کارت و مودم" : (records.first?.storage.title ?? "نامشخص") }
    var hasSIMRecord: Bool { records.contains { $0.storage == .sim } }
    var hasModemRecord: Bool { records.contains { $0.storage == .modem } }

    var initials: String {
        let words = name.split(separator: " ")
        let value = words.prefix(2).compactMap(\.first).map(String.init).joined()
        return value.isEmpty ? "؟" : value
    }
}

struct ConnectedDevice: Identifiable, Sendable, Hashable {
    let id: String
    let name: String
    let mac: String
    let ip: String
    let status: String
    let isOnline: Bool
    let isBlocked: Bool
    let isCurrentMac: Bool
    let connectionType: String
    let durationSeconds: Int
    let lastActive: String
    let receivedBytes: Int64
    let sentBytes: Int64
}

struct DHCPInfo: Sendable {
    let dnsEnabled: Bool
    let dns1: String
    let dns2: String
    let start: String
    let end: String
    let leaseTime: String
    let ip: String

    init(json: [String: Any]) {
        dnsEnabled = String(describing: json["dns_enable"] ?? "0") == "1"
        dns1 = json["dns1"] as? String ?? ""
        dns2 = json["dns2"] as? String ?? ""
        start = json["start"] as? String ?? ""
        end = json["end"] as? String ?? ""
        leaseTime = json["lease_time"] as? String ?? ""
        ip = json["ip"] as? String ?? ""
    }
}

enum DNSProfile: String, CaseIterable, Identifiable, Sendable {
    case off, cloudflareFamily, adguardFamily, custom

    var id: String { rawValue }
    var title: String {
        switch self {
        case .off: "غیرفعال"
        case .cloudflareFamily: "Cloudflare Family"
        case .adguardFamily: "AdGuard Family"
        case .custom: "سفارشی"
        }
    }
    var detail: String {
        switch self {
        case .off: "DNS اپراتور یا مودم"
        case .cloudflareFamily: "فیلتر محتوای بزرگسالان"
        case .adguardFamily: "فیلتر تبلیغات و محتوای نامناسب"
        case .custom: "آدرس دلخواه شما"
        }
    }
    var primary: String {
        switch self {
        case .off: ""
        case .cloudflareFamily: "1.1.1.3"
        case .adguardFamily: "94.140.14.15"
        case .custom: ""
        }
    }
    var secondary: String {
        switch self {
        case .off: ""
        case .cloudflareFamily: "1.0.0.3"
        case .adguardFamily: "94.140.15.16"
        case .custom: ""
        }
    }
}

enum USSDState: Sendable, Equatable {
    case message(String)
    case terminated
    case answeredElsewhere
    case unsupported
    case empty
    case timedOut
    case transport(String)
}

enum RebootPhase: Sendable, Equatable {
    case idle, sending, waitingForOffline, reconnecting, online, timedOut
    var title: String {
        switch self {
        case .idle: "آماده"
        case .sending: "در حال ارسال دستور"
        case .waitingForOffline: "در انتظار قطع اتصال مودم"
        case .reconnecting: "در انتظار بازگشت مودم"
        case .online: "مودم دوباره آنلاین شد"
        case .timedOut: "مودم در زمان مورد انتظار برنگشت"
        }
    }
    var isBusy: Bool {
        switch self { case .sending, .waitingForOffline, .reconnecting: true; default: false }
    }
}

enum LoadFreshness: Sendable, Equatable {
    case idle
    case loading
    case fresh(Date)
    case stale(Date, String)
    case failed(String)

    var hasError: Bool {
        switch self {
        case .stale, .failed: true
        default: false
        }
    }
}

enum ModemError: LocalizedError, Sendable {
    case invalidAddress
    case invalidResponse
    case server(Int)
    case modemRejected
    case contactNameTooLong(Int)
    case currentDeviceProtection
    case invalidDNS(String)
    case unavailable(String)

    var errorDescription: String? {
        switch self {
        case .invalidAddress: "آدرس مودم معتبر نیست."
        case .invalidResponse: "پاسخ مودم قابل خواندن نیست."
        case .server(let code): "مودم با خطای HTTP \(code) پاسخ داد."
        case .modemRejected: "مودم درخواست را نپذیرفت."
        case .contactNameTooLong(let limit): "نام مخاطب برای محل انتخاب‌شده حداکثر \(limit) کاراکتر میتواند باشد."
        case .currentDeviceProtection: "قطع یا مسدودکردن دستگاهی که این اپ روی آن اجرا می‌شود مجاز نیست؛ ارتباط خودتان قطع می‌شود."
        case .invalidDNS(let message): message
        case .unavailable(let message): "ارتباط با مودم برقرار نشد: \(message)"
        }
    }
}

@MainActor
enum Formatters {
    static func bytes(_ count: Int64) -> String {
        ByteCountFormatter.string(fromByteCount: count, countStyle: .decimal)
    }

    static func speed(_ bytesPerSecond: Int64) -> String {
        "\(bytes(bytesPerSecond))/s"
    }

    static func duration(_ seconds: Int) -> String {
        let hours = seconds / 3_600
        let minutes = (seconds % 3_600) / 60
        return hours > 0 ? "\(hours) ساعت و \(minutes) دقیقه" : "\(minutes) دقیقه"
    }
}
