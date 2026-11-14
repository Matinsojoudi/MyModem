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

    var displaySender: String { senderName.isEmpty ? sender : senderName }
}

struct ModemContact: Identifiable, Sendable, Hashable {
    let id: String
    let allIDs: [String]
    let name: String
    let number: String
    let normalizedNumber: String
    let group: String
    let storage: String

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
    case unavailable(String)

    var errorDescription: String? {
        switch self {
        case .invalidAddress: "آدرس مودم معتبر نیست."
        case .invalidResponse: "پاسخ مودم قابل خواندن نیست."
        case .server(let code): "مودم با خطای HTTP \(code) پاسخ داد."
        case .modemRejected: "مودم درخواست را نپذیرفت."
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
