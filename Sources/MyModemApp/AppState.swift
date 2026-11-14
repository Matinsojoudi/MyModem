import AppKit
import Observation
import UserNotifications

@MainActor
@Observable
final class AppState {
    enum Section: String, CaseIterable, Identifiable {
        case dashboard = "نمای کلی"
        case messages = "پیام‌ها"
        case ussd = "کد دستوری"
        case devices = "دستگاه‌ها"
        case fileShare = "اشتراک فایل"
        case settings = "تنظیمات"
        var id: String { rawValue }
        var symbol: String {
            switch self {
            case .dashboard: "gauge.with.dots.needle.67percent"
            case .messages: "message.fill"
            case .ussd: "number.square.fill"
            case .devices: "wifi.router.fill"
            case .fileShare: "square.and.arrow.up.fill"
            case .settings: "gearshape.fill"
            }
        }
    }

    var selection: Section = .dashboard
    var status: ModemStatus?
    var messages: [SMSMessage] = []
    var contacts: [ModemContact] = []
    var devices: [ConnectedDevice] = []
    var isRefreshing = false
    var isOnline = false
    var lastUpdated: Date?
    var statusFreshness: LoadFreshness = .idle
    var messagesFreshness: LoadFreshness = .idle
    var contactsFreshness: LoadFreshness = .idle
    var devicesFreshness: LoadFreshness = .idle
    var errorMessage: String?
    var host: String {
        didSet { UserDefaults.standard.set(host, forKey: "modemHost") }
    }
    var recipient = ""
    var draft = ""
    var ussdCode = "*100#"
    var ussdResponse = ""
    var isSending = false
    let fileShare = FileShareServer()

    private let client: ModemClient
    private var refreshTask: Task<Void, Never>?
    private var previouslySeen: Set<String>
    private var firstMessageLoad: Bool
    private var alertedLowBattery: Bool
    private var alertedCriticalBattery: Bool

    init() {
        let savedHost = UserDefaults.standard.string(forKey: "modemHost") ?? "192.168.1.1"
        host = savedHost
        client = ModemClient(host: savedHost)
        let restoredSeen = Set(UserDefaults.standard.stringArray(forKey: "seenSMSIDs") ?? [])
        previouslySeen = restoredSeen
        firstMessageLoad = restoredSeen.isEmpty
        alertedLowBattery = UserDefaults.standard.bool(forKey: "alertedLowBattery")
        alertedCriticalBattery = UserDefaults.standard.bool(forKey: "alertedCriticalBattery")
    }

    func start() {
        guard refreshTask == nil else { return }
        requestNotifications()
        refreshTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.refresh()
                try? await Task.sleep(for: .seconds(30))
            }
        }
    }

    func stop() { refreshTask?.cancel(); refreshTask = nil; fileShare.stop() }

    func refresh() async {
        guard !isRefreshing else { return }
        isRefreshing = true
        defer { isRefreshing = false }
        do {
            try await client.updateHost(host)
        } catch {
            isOnline = false
            errorMessage = error.localizedDescription
            let message = error.localizedDescription
            statusFreshness = fail(previous: statusFreshness, message: message)
            messagesFreshness = fail(previous: messagesFreshness, message: message)
            contactsFreshness = fail(previous: contactsFreshness, message: message)
            devicesFreshness = fail(previous: devicesFreshness, message: message)
            return
        }

        statusFreshness = .loading
        messagesFreshness = .loading
        contactsFreshness = .loading
        devicesFreshness = .loading

        async let statusResult = capture { try await self.client.status() }
        async let messagesResult = capture { try await self.client.messages() }
        async let contactsResult = capture { try await self.client.contacts() }
        async let devicesResult = capture { try await self.client.devices() }
        let (nextStatus, nextMessages, nextContacts, nextDevices) = await (statusResult, messagesResult, contactsResult, devicesResult)
        let now = Date()

        switch nextStatus {
        case .success(let value): status = value; statusFreshness = .fresh(now); isOnline = true; lastUpdated = now; evaluateBatteryAlerts(value)
        case .failure(let error): statusFreshness = fail(previous: statusFreshness, message: error.localizedDescription); isOnline = false
        }
        switch nextContacts {
        case .success(let value): contacts = value; contactsFreshness = .fresh(now)
        case .failure(let error): contactsFreshness = fail(previous: contactsFreshness, message: error.localizedDescription)
        }
        switch nextMessages {
        case .success(let value): messages = resolvedMessages(value, contacts: contacts); messagesFreshness = .fresh(now); notifyAboutNewMessages(value)
        case .failure(let error): messagesFreshness = fail(previous: messagesFreshness, message: error.localizedDescription)
        }
        switch nextDevices {
        case .success(let value): devices = value; devicesFreshness = .fresh(now)
        case .failure(let error): devicesFreshness = fail(previous: devicesFreshness, message: error.localizedDescription)
        }

        let failures = [statusFreshness, messagesFreshness, contactsFreshness, devicesFreshness].filter(\.hasError).count
        errorMessage = failures == 4 ? "ارتباط با هیچ‌یک از بخش‌های مودم برقرار نشد." : nil
    }

    private func capture<T: Sendable>(_ operation: @escaping @Sendable () async throws -> T) async -> Result<T, any Error> {
        do { return .success(try await operation()) }
        catch { return .failure(error) }
    }

    private func fail(previous: LoadFreshness, message: String) -> LoadFreshness {
        switch previous {
        case .fresh(let date), .stale(let date, _): .stale(date, message)
        default: .failed(message)
        }
    }

    func compose(to contact: ModemContact) {
        recipient = contact.number
    }

    private func resolvedMessages(_ messages: [SMSMessage], contacts: [ModemContact]) -> [SMSMessage] {
        let codec = ModemCodec()
        let names = Dictionary(uniqueKeysWithValues: contacts.compactMap { contact in
            contact.normalizedNumber.isEmpty ? nil : (contact.normalizedNumber, contact.name)
        })
        return messages.map { message in
            let normalized = codec.normalizePhone(message.sender)
            let matchedName = names[normalized] ?? message.senderName
            return SMSMessage(id: message.id, sender: message.sender, senderName: matchedName, text: message.text, rawTime: message.rawTime, displayTime: message.displayTime, isUnread: message.isUnread, isMissedCall: message.isMissedCall, callerNumber: message.callerNumber, storage: message.storage)
        }
    }

    func sendMessage() async {
        isSending = true
        defer { isSending = false }
        do {
            try await client.sendSMS(to: recipient, text: draft)
            draft = ""
            errorMessage = nil
            await refresh()
        } catch { errorMessage = error.localizedDescription }
    }

    func markRead(_ message: SMSMessage) async {
        do { try await client.markRead(message); await refresh() }
        catch { errorMessage = error.localizedDescription }
    }

    func delete(_ message: SMSMessage) async {
        do { try await client.delete(message); await refresh() }
        catch { errorMessage = error.localizedDescription }
    }

    func sendUSSD() async {
        isSending = true
        defer { isSending = false }
        do { ussdResponse = try await client.sendUSSD(ussdCode); errorMessage = nil }
        catch { errorMessage = error.localizedDescription }
    }

    func manage(_ device: ConnectedDevice, action: String) async {
        do { try await client.manageDevice(device, action: action); await refresh() }
        catch { errorMessage = error.localizedDescription }
    }

    func reboot() async {
        do { try await client.reboot(); errorMessage = nil }
        catch { errorMessage = error.localizedDescription }
    }

    private func requestNotifications() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }

    private func evaluateBatteryAlerts(_ value: ModemStatus) {
        if value.isCharging || value.batteryPercent > 15 {
            alertedLowBattery = false
            alertedCriticalBattery = false
        } else if value.batteryPercent <= 5, !alertedCriticalBattery {
            deliverNotification(id: "battery-critical", title: "باتری مودم بحرانی است", body: "شارژ مودم به \(value.batteryPercent)٪ رسیده؛ فوراً شارژر را متصل کنید.")
            alertedCriticalBattery = true
            alertedLowBattery = true
        } else if value.batteryPercent <= 10, !alertedLowBattery {
            deliverNotification(id: "battery-low", title: "شارژ مودم کم است", body: "باتری مودم \(value.batteryPercent)٪ است؛ آن را به برق متصل کنید.")
            alertedLowBattery = true
        }
        UserDefaults.standard.set(alertedLowBattery, forKey: "alertedLowBattery")
        UserDefaults.standard.set(alertedCriticalBattery, forKey: "alertedCriticalBattery")
    }

    private func deliverNotification(id: String, title: String, body: String) {
        let content = UNMutableNotificationContent()
        content.title = title
        content.body = body
        content.sound = .default
        UNUserNotificationCenter.current().add(.init(identifier: id, content: content, trigger: nil))
    }

    private func notifyAboutNewMessages(_ loaded: [SMSMessage]) {
        let current = Set(loaded.map(\.id))
        defer {
            previouslySeen.formUnion(current)
            if previouslySeen.count > 500 { previouslySeen = Set(loaded.prefix(500).map(\.id)) }
            UserDefaults.standard.set(Array(previouslySeen), forKey: "seenSMSIDs")
            firstMessageLoad = false
        }
        guard !firstMessageLoad else { return }
        for message in loaded where !previouslySeen.contains(message.id) {
            let content = UNMutableNotificationContent()
            content.title = message.isMissedCall ? "تماس ازدست‌رفته" : "پیام جدید از \(message.displaySender)"
            content.body = message.isMissedCall ? (message.callerNumber.isEmpty ? message.sender : message.callerNumber) : String(message.text.prefix(120))
            content.sound = .default
            UNUserNotificationCenter.current().add(.init(identifier: message.id, content: content, trigger: nil))
        }
    }
}
