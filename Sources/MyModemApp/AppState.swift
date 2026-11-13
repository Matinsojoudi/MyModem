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
    private var previouslySeen = Set<String>()
    private var firstMessageLoad = true

    init() {
        let savedHost = UserDefaults.standard.string(forKey: "modemHost") ?? "192.168.1.1"
        host = savedHost
        client = ModemClient(host: savedHost)
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
        await client.updateHost(host)
        do {
            async let nextStatus = client.status()
            async let nextMessages = client.messages()
            async let nextContacts = client.contacts()
            async let nextDevices = client.devices()
            let loadedStatus = try await nextStatus
            let loadedMessages = try await nextMessages
            let loadedContacts = try await nextContacts
            let loadedDevices = try await nextDevices
            status = loadedStatus
            contacts = loadedContacts
            messages = resolvedMessages(loadedMessages, contacts: loadedContacts)
            devices = loadedDevices
            isOnline = true
            lastUpdated = Date()
            errorMessage = nil
            notifyAboutNewMessages(loadedMessages)
        } catch {
            isOnline = false
            errorMessage = error.localizedDescription
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

    private func notifyAboutNewMessages(_ loaded: [SMSMessage]) {
        let current = Set(loaded.map(\.id))
        defer { previouslySeen.formUnion(current); firstMessageLoad = false }
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
