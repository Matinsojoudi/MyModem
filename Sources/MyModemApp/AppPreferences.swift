import Foundation
import Observation
import ServiceManagement
import SwiftUI

@MainActor
@Observable
final class AppPreferences {
    var refreshSeconds: Int {
        didSet { UserDefaults.standard.set(refreshSeconds, forKey: "refreshSeconds") }
    }
    var notificationsEnabled: Bool {
        didSet { UserDefaults.standard.set(notificationsEnabled, forKey: "notificationsEnabled") }
    }
    var batteryAlertsEnabled: Bool {
        didSet { UserDefaults.standard.set(batteryAlertsEnabled, forKey: "batteryAlertsEnabled") }
    }
    var retentionDays: Int {
        didSet { UserDefaults.standard.set(retentionDays, forKey: "retentionDays") }
    }
    private(set) var launchAtLogin: Bool
    private(set) var launchErrorMessage: String?

    init() {
        let defaults = UserDefaults.standard
        refreshSeconds = defaults.object(forKey: "refreshSeconds") as? Int ?? 30
        notificationsEnabled = defaults.object(forKey: "notificationsEnabled") as? Bool ?? true
        batteryAlertsEnabled = defaults.object(forKey: "batteryAlertsEnabled") as? Bool ?? true
        retentionDays = defaults.object(forKey: "retentionDays") as? Int ?? 7
        launchAtLogin = SMAppService.mainApp.status == .enabled
    }

    func setLaunchAtLogin(_ enabled: Bool) {
        do {
            if enabled { try SMAppService.mainApp.register() }
            else { try SMAppService.mainApp.unregister() }
            launchAtLogin = SMAppService.mainApp.status == .enabled
            launchErrorMessage = nil
        } catch {
            launchErrorMessage = "ثبت اجرای خودکار ممکن نشد: \(error.localizedDescription)"
            launchAtLogin = SMAppService.mainApp.status == .enabled
        }
    }

    func purge(chat: ChatManager, library: FileLibrary) {
        let cutoff = Date().addingTimeInterval(-TimeInterval(retentionDays * 86_400))
        library.purgeExpired()
        for room in chat.rooms where room.messages.allSatisfy({ $0.createdAt < cutoff }) && room.createdAt < cutoff {
            chat.deleteRoom(room)
        }
    }
}

@MainActor
enum Diagnostics {
    static func report(state: AppState, preferences: AppPreferences) -> String {
        let version = Bundle.main.object(forInfoDictionaryKey: "CFBundleShortVersionString") as? String ?? "dev"
        let lines = [
            "MyModem \(version)",
            "macOS \(ProcessInfo.processInfo.operatingSystemVersionString)",
            "host=\(state.host)",
            "online=\(state.isOnline)",
            "status=\(state.status.map { "\($0.batteryPercent)%" } ?? "-")",
            "messages=\(state.messages.count) conversations=\(state.conversations.count) contacts=\(state.contacts.count) devices=\(state.devices.count)",
            "freshness: status=\(label(state.statusFreshness)) messages=\(label(state.messagesFreshness)) contacts=\(label(state.contactsFreshness)) devices=\(label(state.devicesFreshness))",
            "refreshSeconds=\(preferences.refreshSeconds) notifications=\(preferences.notificationsEnabled) batteryAlerts=\(preferences.batteryAlertsEnabled)",
            "libraryFiles=\(state.lanHub.library.files.count) libraryBytes=\(state.lanHub.library.totalSize)",
            "pairedDevices=\(state.lanHub.auth.pairedDevices.count) chatRooms=\(state.lanHub.chat.rooms.count)",
            "lastError=\(state.errorMessage ?? "-")",
            "generated=\(ISO8601DateFormatter().string(from: Date()))"
        ]
        return lines.joined(separator: "\n") + "\n"
    }

    private static func label(_ value: LoadFreshness) -> String {
        switch value {
        case .idle: "idle"
        case .loading: "loading"
        case .fresh: "fresh"
        case .stale: "stale"
        case .failed: "failed"
        }
    }

    static func export(_ content: String) {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "mymodem-diagnostics.txt"
        panel.canCreateDirectories = true
        guard panel.runModal() == .OK, let url = panel.url else { return }
        try? Data(content.utf8).write(to: url, options: .atomic)
    }
}
