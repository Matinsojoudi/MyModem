import CryptoKit
import Foundation
import Observation
import Security

struct PairedDevice: Codable, Identifiable, Sendable, Hashable {
    let id: String
    var name: String
    var tokenHash: String
    var pairedAt: Date
    var lastSeen: Date
}

struct PairingCode: Sendable, Equatable {
    let code: String
    let expiresAt: Date
    var isExpired: Bool { Date() >= expiresAt }
}

@MainActor
@Observable
final class LANAuth {
    private(set) var pairedDevices: [PairedDevice] = []
    private(set) var activeCode: PairingCode?
    private var failedAttempts = 0
    private var sessions: [String: String] = [:]   // tokenHash -> deviceID

    private let storeURL: URL

    init(baseDirectory: URL? = nil) {
        let base = baseDirectory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appending(path: "MyModem", directoryHint: .isDirectory)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        storeURL = base.appending(path: "paired-devices.json")
        load()
    }

    func beginPairing() -> PairingCode {
        let code = String(format: "%06d", Int.random(in: 0...999_999))
        let value = PairingCode(code: code, expiresAt: Date().addingTimeInterval(300))
        activeCode = value
        failedAttempts = 0
        return value
    }

    func cancelPairing() { activeCode = nil }

    func redeem(code: String, deviceName: String) -> String? {
        guard let expected = activeCode, !expected.isExpired else { activeCode = nil; return nil }
        guard failedAttempts < 5 else { activeCode = nil; return nil }
        let provided = code.filter(\.isNumber)
        guard Self.constantTimeEquals(provided, expected.code) else {
            failedAttempts += 1
            return nil
        }
        activeCode = nil
        failedAttempts = 0
        let token = Self.randomToken()
        let hash = Self.hash(token)
        let device = PairedDevice(id: UUID().uuidString, name: deviceName.isEmpty ? "دستگاه مهمان" : deviceName, tokenHash: hash, pairedAt: Date(), lastSeen: Date())
        pairedDevices.append(device)
        sessions[hash] = device.id
        save()
        return token
    }

    func authorize(token: String) -> PairedDevice? {
        let hash = Self.hash(token)
        guard let deviceID = sessions[hash] ?? pairedDevices.first(where: { $0.tokenHash == hash })?.id,
              let index = pairedDevices.firstIndex(where: { $0.id == deviceID })
        else { return nil }
        sessions[hash] = deviceID
        pairedDevices[index].lastSeen = Date()
        return pairedDevices[index]
    }

    func revoke(_ device: PairedDevice) {
        pairedDevices.removeAll { $0.id == device.id }
        sessions = sessions.filter { $0.value != device.id }
        save()
    }

    func revokeAll() {
        pairedDevices.removeAll()
        sessions.removeAll()
        save()
    }

    private func load() {
        guard let data = try? Data(contentsOf: storeURL),
              let values = try? JSONDecoder().decode([PairedDevice].self, from: data) else { return }
        pairedDevices = values
    }

    private func save() {
        if let data = try? JSONEncoder().encode(pairedDevices) {
            try? data.write(to: storeURL, options: .atomic)
        }
    }

    nonisolated static func hash(_ token: String) -> String {
        SHA256.hash(data: Data(token.utf8)).map { String(format: "%02x", $0) }.joined()
    }

    nonisolated static func randomToken() -> String {
        var bytes = [UInt8](repeating: 0, count: 32)
        guard SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes) == errSecSuccess else { return "" }
        return bytes.map { String(format: "%02x", $0) }.joined()
    }

    nonisolated static func constantTimeEquals(_ input: String, _ expected: String) -> Bool {
        let lhs = Array(input.utf8), rhs = Array(expected.utf8)
        var difference = UInt8(truncatingIfNeeded: lhs.count ^ rhs.count)
        for index in 0..<max(lhs.count, rhs.count) {
            difference |= (index < lhs.count ? lhs[index] : 0) ^ (index < rhs.count ? rhs[index] : 0)
        }
        return difference == 0
    }
}
