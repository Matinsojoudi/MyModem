import AppKit
import Observation
import UniformTypeIdentifiers
import UserNotifications

@MainActor
@Observable
final class AppState {
    enum Section: String, CaseIterable, Identifiable {
        case dashboard = "نمای کلی"
        case messages = "پیام‌ها"
        case ussd = "کد دستوری"
        case devices = "دستگاه‌ها"
        case network = "شبکه و DNS"
        case fileShare = "ارسال سریع"
        case transfer = "کتابخانه و کلیپ‌بورد"
        case chat = "گفتگوی LAN"
        case settings = "تنظیمات"
        var id: String { rawValue }
        var symbol: String {
            switch self {
            case .dashboard: "gauge.with.dots.needle.67percent"
            case .messages: "message.fill"
            case .ussd: "number.square.fill"
            case .devices: "wifi.router.fill"
            case .network: "network"
            case .fileShare: "square.and.arrow.up.fill"
            case .transfer: "folder.badge.gearshape"
            case .chat: "bubble.left.and.bubble.right.fill"
            case .settings: "gearshape.fill"
            }
        }
    }

    var selection: Section = .dashboard
    var status: ModemStatus?
    var messages: [SMSMessage] = []
    var sentMessages: [SMSMessage] = []
    var conversations: [Conversation] = []
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
    var dnsInfo: DHCPInfo?
    var dnsProfile: DNSProfile = .off
    var customDNS1 = ""
    var customDNS2 = ""
    var rebootPhase: RebootPhase = .idle
    let fileShare = FileShareServer()
    let lanHub = LANHub()
    let preferences = AppPreferences()

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
        if preferences.notificationsEnabled { requestNotifications() }
        refreshTask = Task { [weak self] in
            while !Task.isCancelled {
                await self?.refresh()
                try? await Task.sleep(for: .seconds(self?.preferences.refreshSeconds ?? 30))
            }
        }
    }

    func stop() { refreshTask?.cancel(); refreshTask = nil; fileShare.stop(); lanHub.stop() }

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
        async let sentResult = capture { try await self.client.sentMessages() }
        async let contactsResult = capture { try await self.client.contacts() }
        async let devicesResult = capture { try await self.client.devices() }
        let (nextStatus, nextMessages, nextSent, nextContacts, nextDevices) = await (statusResult, messagesResult, sentResult, contactsResult, devicesResult)
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
        if case .success(let value) = nextSent { sentMessages = resolvedMessages(value, contacts: contacts) }
        conversations = buildConversations(incoming: messages, outgoing: sentMessages, contacts: contacts)
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

    func addContact(name: String, number: String, group: ContactGroup, storage: ContactStorage) async -> Bool {
        do {
            try await client.addContact(name: name, number: number, group: group, storage: storage)
            contacts = try await client.contacts()
            contactsFreshness = .fresh(Date())
            return true
        } catch { errorMessage = error.localizedDescription; return false }
    }

    func replaceContact(_ oldRecord: ContactRecord, name: String, number: String, group: ContactGroup, storage: ContactStorage) async -> Bool {
        do {
            try await client.addContact(name: name, number: number, group: group, storage: storage)
            let afterAdd = try await client.contacts()
            let normalized = ModemCodec().normalizePhone(number)
            guard afterAdd.contains(where: { contact in contact.normalizedNumber == normalized && contact.records.contains { $0.storage == storage } }) else {
                errorMessage = "مخاطب جدید روی مودم تأیید نشد؛ نسخهٔ قبلی حذف نشد."
                return false
            }
            try await client.deleteContactRecords(ids: [oldRecord.id])
            contacts = try await client.contacts()
            contactsFreshness = .fresh(Date())
            return true
        } catch { errorMessage = error.localizedDescription; return false }
    }

    func deleteContact(_ contact: ModemContact, storage: ContactStorage? = nil) async -> Bool {
        let ids = contact.records.filter { storage == nil || $0.storage == storage }.map(\.id)
        do {
            try await client.deleteContactRecords(ids: ids)
            contacts = try await client.contacts()
            contactsFreshness = .fresh(Date())
            return true
        } catch { errorMessage = error.localizedDescription; return false }
    }

    func exportContacts(format: ContactExportFormat) {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = format == .vcard ? "mymodem-contacts.vcf" : "mymodem-contacts.csv"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        let content = format == .vcard ? ContactCodec.vCard(contacts) : ContactCodec.csv(contacts)
        try? Data(content.utf8).write(to: url, options: .atomic)
    }

    func importContacts(storage: ContactStorage) async -> (added: Int, skipped: Int) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.allowedContentTypes = [.commaSeparatedText, .vCard, .plainText]
        guard panel.runModal() == .OK, let url = panel.url,
              let text = try? String(contentsOf: url, encoding: .utf8) else { return (0, 0) }
        let parsed = ContactCodec.parse(text)
        let existing = Set(contacts.map(\.normalizedNumber))
        let codec = ModemCodec()
        var added = 0, skipped = 0
        for entry in parsed {
            let normalized = codec.normalizePhone(entry.number)
            guard !normalized.isEmpty, !existing.contains(normalized) else { skipped += 1; continue }
            if await addContact(name: entry.name, number: entry.number, group: entry.group, storage: storage) { added += 1 }
            else { skipped += 1 }
        }
        return (added, skipped)
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
            return SMSMessage(id: message.id, sender: message.sender, senderName: matchedName, text: message.text, rawTime: message.rawTime, displayTime: message.displayTime, isUnread: message.isUnread, isMissedCall: message.isMissedCall, callerNumber: message.callerNumber, storage: message.storage, direction: message.direction)
        }
    }

    private func buildConversations(incoming: [SMSMessage], outgoing: [SMSMessage], contacts: [ModemContact]) -> [Conversation] {
        let codec = ModemCodec()
        let names = Dictionary(uniqueKeysWithValues: contacts.compactMap { $0.normalizedNumber.isEmpty ? nil : ($0.normalizedNumber, $0.name) })
        let grouped = Dictionary(grouping: incoming + outgoing) { message in codec.normalizePhone(message.sender) }
        return grouped.compactMap { peer, messages in
            guard !peer.isEmpty else { return nil }
            let sorted = messages.sorted { $0.rawTime < $1.rawTime }
            return Conversation(peerNumber: peer, displayName: names[peer] ?? sorted.first?.displaySender ?? peer, messages: sorted)
        }.sorted { ($0.lastMessage?.rawTime ?? "") > ($1.lastMessage?.rawTime ?? "") }
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

    func markConversationRead(_ conversation: Conversation) async {
        let count = await client.markRead(conversation.messages)
        guard count > 0 else { return }
        await refresh()
    }

    func delete(_ message: SMSMessage) async {
        do { try await client.delete(message); await refresh() }
        catch { errorMessage = error.localizedDescription }
    }

    func sendUSSD() async {
        isSending = true
        defer { isSending = false }
        switch await client.sendUSSD(ussdCode) {
        case .message(let text): ussdResponse = text; errorMessage = nil
        case .terminated: ussdResponse = "نشست USSD را شبکه بست. مودم‌های دیتا معمولاً کانال صوتی/سیگنالینگ کامل برای USSD ندارند؛ از پنل اپراتور استفاده کنید."
        case .answeredElsewhere: ussdResponse = "نشست USSD توسط ارتباط دیگری پاسخ داده شد."
        case .unsupported: ussdResponse = "این کد دستوری توسط اپراتور پشتیبانی نمی‌شود."
        case .empty: ussdResponse = "درخواست ارسال شد اما اپراتور متنی برنگرداند."
        case .timedOut: ussdResponse = "زمان انتظار برای پاسخ شبکه تمام شد."
        case .transport(let message): ussdResponse = ""; errorMessage = message
        }
    }

    func manage(_ device: ConnectedDevice, action: String) async {
        do { try await client.manageDevice(device, action: action); await refresh() }
        catch { errorMessage = error.localizedDescription }
    }

    func resetTraffic() async {
        do { try await client.resetTraffic(); await refresh() }
        catch { errorMessage = error.localizedDescription }
    }

    func loadDNS() async {
        do {
            dnsInfo = try await client.dhcpInfo()
            if !dnsInfo!.dnsEnabled { dnsProfile = .off }
            else if dnsInfo!.dns1 == DNSProfile.cloudflareFamily.primary { dnsProfile = .cloudflareFamily }
            else if dnsInfo!.dns1 == DNSProfile.adguardFamily.primary { dnsProfile = .adguardFamily }
            else { dnsProfile = .custom; customDNS1 = dnsInfo!.dns1; customDNS2 = dnsInfo!.dns2 }
        } catch { errorMessage = error.localizedDescription }
    }

    func applyDNS() async -> Bool {
        isSending = true
        defer { isSending = false }
        do {
            try await client.applyDNS(dnsProfile, primary: customDNS1, secondary: customDNS2)
            await loadDNS()
            return true
        } catch { errorMessage = error.localizedDescription; return false }
    }

    func reboot() async {
        rebootPhase = .sending
        do {
            try await client.reboot()
            rebootPhase = .waitingForOffline
            var sawOffline = false
            for _ in 0..<40 {
                try? await Task.sleep(for: .seconds(2))
                if (try? await client.status()) != nil {
                    if sawOffline { rebootPhase = .online; await refresh(); return }
                } else { sawOffline = true; rebootPhase = .reconnecting }
            }
            rebootPhase = sawOffline ? .timedOut : .online
        } catch { rebootPhase = .idle; errorMessage = error.localizedDescription }
    }

    private func requestNotifications() {
        UNUserNotificationCenter.current().requestAuthorization(options: [.alert, .sound]) { _, _ in }
    }

    private func evaluateBatteryAlerts(_ value: ModemStatus) {
        guard preferences.batteryAlertsEnabled else { return }
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
        guard preferences.notificationsEnabled else { return }
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
