import SwiftUI

struct RootView: View {
    @Bindable var state: AppState
    var body: some View {
        HStack(spacing: 0) {
            BrandSidebar(state: state).frame(width: 236)
            ZStack {
                ModemTheme.canvas.ignoresSafeArea()
                Group {
                    switch state.selection {
                    case .dashboard: DashboardView(state: state)
                    case .messages: MessagesView(state: state)
                    case .ussd: USSDView(state: state)
                    case .devices: DevicesView(state: state)
                    case .network: NetworkView(state: state)
                    case .fileShare: FileShareView(server: state.fileShare)
                    case .transfer: TransferView(hub: state.lanHub)
                    case .chat: ChatView(hub: state.lanHub)
                    case .settings: SettingsView(state: state)
                    }
                }
                .transition(.opacity.combined(with: .scale(scale: 0.992)))
                .id(state.selection)
            }
        }
        .environment(\.layoutDirection, .rightToLeft)
        .environment(\.colorScheme, .light)
        .tint(ModemTheme.blue)
        .animation(.easeOut(duration: 0.18), value: state.selection)
        .alert("خطا", isPresented: Binding(get: { state.errorMessage != nil }, set: { if !$0 { state.errorMessage = nil } })) { Button("باشه") { state.errorMessage = nil } } message: { Text(state.errorMessage ?? "") }
        .frame(minWidth: 1020, minHeight: 680)
    }
}

struct BrandSidebar: View {
    @Bindable var state: AppState
    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(spacing: 12) {
                BrandMark(size: 44)
                VStack(alignment: .leading, spacing: 1) {
                    Text("MyModem").font(.system(size: 19, weight: .bold, design: .rounded)).foregroundStyle(.white)
                    Text("مرکز کنترل مودم").font(.caption).foregroundStyle(.white.opacity(0.78))
                }
            }.padding(.horizontal, 20).padding(.top, 24).padding(.bottom, 30)
            VStack(spacing: 7) {
                ForEach(AppState.Section.allCases) { section in
                    Button { state.selection = section } label: {
                        HStack(spacing: 12) {
                            Image(systemName: section.symbol).font(.system(size: 15, weight: .semibold)).frame(width: 22)
                            Text(section.rawValue).font(.system(size: 14, weight: .medium, design: .rounded))
                            Spacer()
                        }
                        .foregroundStyle(state.selection == section ? ModemTheme.navy : .white.opacity(0.78))
                        .padding(.horizontal, 14)
                        .frame(maxWidth: .infinity, minHeight: 44, maxHeight: 44, alignment: .leading)
                        .background(state.selection == section ? Color.white : Color.clear, in: RoundedRectangle(cornerRadius: 13, style: .continuous))
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .frame(maxWidth: .infinity)
                }
            }.padding(.horizontal, 12)
            Spacer()
            VStack(alignment: .leading, spacing: 12) {
                HStack(spacing: 9) {
                    ZStack { Circle().fill((state.isOnline ? ModemTheme.success : ModemTheme.danger).opacity(0.2)).frame(width: 24, height: 24); Circle().fill(state.isOnline ? ModemTheme.success : ModemTheme.danger).frame(width: 8, height: 8) }
                    VStack(alignment: .leading, spacing: 1) { Text(state.isOnline ? "مودم متصل است" : "مودم آفلاین است").font(.caption.bold()); Text(state.host).font(.caption2).opacity(0.6) }
                    Spacer()
                }
                Button { Task { await state.refresh() } } label: { Label(state.isRefreshing ? "در حال بروزرسانی" : "تازه‌سازی", systemImage: "arrow.clockwise").frame(maxWidth: .infinity) }
                    .buttonStyle(.borderless).foregroundStyle(.white.opacity(0.8)).disabled(state.isRefreshing)
            }
            .foregroundStyle(.white).padding(16)
            .background(.white.opacity(0.07), in: RoundedRectangle(cornerRadius: 17, style: .continuous))
            .padding(14)
        }
        .background(LinearGradient(colors: [ModemTheme.navyRaised, ModemTheme.navy], startPoint: .topLeading, endPoint: .bottomTrailing))
        .environment(\.layoutDirection, .rightToLeft)
    }
}

struct DashboardView: View {
    let state: AppState
    private let columns = [GridItem(.adaptive(minimum: 190), spacing: 14)]
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 22) {
                PageHeader(title: "حال مودم چطور است؟", subtitle: state.lastUpdated.map { "آخرین بروزرسانی ساعت \($0.formatted(date: .omitted, time: .shortened))" } ?? "در انتظار نخستین اتصال")
                if let status = state.status {
                    HeroStatus(status: status)
                    LazyVGrid(columns: columns, spacing: 14) {
                        MetricCard(title: "قدرت سیگنال", value: "\(status.signalQuality) / ۵", detail: signalLabel(status.signalQuality), symbol: "antenna.radiowaves.left.and.right", tint: ModemTheme.blue)
                        MetricCard(title: "دستگاه‌های متصل", value: "\(status.connectedClients)", detail: "روی شبکهٔ Wi-Fi", symbol: "laptopcomputer.and.iphone", tint: ModemTheme.sky)
                        MetricCard(title: "پیام تازه", value: "\(status.unreadMessages)", detail: status.unreadMessages == 0 ? "همه خوانده شده‌اند" : "در انتظار شما", symbol: "envelope.fill", tint: ModemTheme.warning)
                        MetricCard(title: "زمان فعالیت", value: Formatters.duration(status.uptimeSeconds), detail: "از آخرین راه‌اندازی", symbol: "clock.fill", tint: ModemTheme.navyRaised)
                    }
                    HStack(spacing: 14) {
                        TrafficCard(title: "دانلود", speed: Formatters.speed(status.downloadSpeed), total: Formatters.bytes(status.receivedBytes), symbol: "arrow.down", tint: ModemTheme.blue)
                        TrafficCard(title: "آپلود", speed: Formatters.speed(status.uploadSpeed), total: Formatters.bytes(status.sentBytes), symbol: "arrow.up", tint: ModemTheme.success)
                    }
                } else { OfflineState() }
            }.padding(30)
        }
    }
    private func signalLabel(_ value: Int) -> String { [0: "بدون سیگنال", 1: "بسیار ضعیف", 2: "ضعیف", 3: "متوسط", 4: "خوب", 5: "عالی"][value] ?? "نامشخص" }
}

struct HeroStatus: View {
    let status: ModemStatus
    var body: some View {
        HStack(spacing: 26) {
            ZStack {
                Circle().stroke(.white.opacity(0.16), lineWidth: 10)
                Circle().trim(from: 0, to: CGFloat(status.batteryPercent) / 100).stroke(.white, style: StrokeStyle(lineWidth: 10, lineCap: .round)).rotationEffect(.degrees(-90))
                VStack(spacing: 0) { Text("\(status.batteryPercent)%").font(.system(size: 27, weight: .bold, design: .rounded)); Image(systemName: status.isCharging ? "bolt.fill" : "battery.75percent").font(.caption) }
            }.frame(width: 108, height: 108)
            VStack(alignment: .leading, spacing: 8) {
                Text(status.isCharging ? "مودم در حال شارژ است" : "مودم آمادهٔ کار است").font(.system(size: 24, weight: .bold, design: .rounded))
                Text(status.isCharging ? "باتری در حال پر شدن است؛ اتصال شبکه پایدار مانده." : "باتری در حال مصرف است؛ وضعیت شبکه را از اینجا دنبال کنید.").foregroundStyle(.white.opacity(0.90)).frame(maxWidth: 460, alignment: .leading)
            }
            Spacer()
            Image(systemName: "wifi.router.fill").font(.system(size: 72, weight: .light)).foregroundStyle(.white.opacity(0.18))
        }.foregroundStyle(.white).padding(26).background(LinearGradient(colors: [ModemTheme.blue, ModemTheme.navyRaised], startPoint: .topLeading, endPoint: .bottomTrailing), in: RoundedRectangle(cornerRadius: 25, style: .continuous)).shadow(color: ModemTheme.navy.opacity(0.16), radius: 24, y: 12)
    }
}

struct MetricCard: View {
    let title: String; let value: String; let detail: String; let symbol: String; let tint: Color
    var body: some View { SoftCard { VStack(alignment: .leading, spacing: 13) { ZStack { RoundedRectangle(cornerRadius: 11).fill(tint.opacity(0.13)); Image(systemName: symbol).foregroundStyle(tint) }.frame(width: 39, height: 39); Text(title).font(.caption).foregroundStyle(ModemTheme.muted); Text(value).font(.system(size: 23, weight: .bold, design: .rounded)).lineLimit(1).minimumScaleFactor(0.75); Text(detail).font(.caption).foregroundStyle(ModemTheme.muted) }.frame(maxWidth: .infinity, alignment: .leading) } }
}

struct TrafficCard: View {
    let title: String; let speed: String; let total: String; let symbol: String; let tint: Color
    var body: some View { SoftCard { HStack(spacing: 15) { ZStack { Circle().fill(tint.opacity(0.13)); Image(systemName: symbol).font(.headline.bold()).foregroundStyle(tint) }.frame(width: 48, height: 48); VStack(alignment: .leading, spacing: 3) { Text(title).font(.caption).foregroundStyle(ModemTheme.muted); Text(speed).font(.title3.bold()).monospacedDigit(); Text("مجموع \(total)").font(.caption2).foregroundStyle(ModemTheme.muted) }; Spacer() }.frame(maxWidth: .infinity) } }
}

struct MessagesView: View {
    enum Mode: String, CaseIterable, Identifiable { case conversations = "گفتگوها"; case inbox = "صندوق‌ها"; case contacts = "مخاطبین"; var id: String { rawValue } }
    @Bindable var state: AppState
    @State private var selected: SMSMessage?
    @State private var mode: Mode = .conversations
    @State private var selectedConversation: Conversation?
    @State private var contactSearch = ""
    @State private var contactStorageFilter: ContactStorage?
    @State private var showingAddContact = false
    @State private var editingRecord: ContactRecord?
    @State private var deletingContact: ModemContact?

    private var filteredContacts: [ModemContact] {
        let query = contactSearch.trimmingCharacters(in: .whitespacesAndNewlines)
        return state.contacts.filter { contact in
            let matchesStorage = contactStorageFilter == nil || contact.records.contains { $0.storage == contactStorageFilter }
            let matchesQuery = query.isEmpty || contact.name.localizedCaseInsensitiveContains(query) || contact.records.contains { $0.number.localizedCaseInsensitiveContains(query) }
            return matchesStorage && matchesQuery
        }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                PageHeader(title: "پیام‌ها", subtitle: "صندوق و مخاطبین ذخیره‌شده روی مودم")
                Spacer()
                Picker("نمایش", selection: $mode) { ForEach(Mode.allCases) { Text($0.rawValue).tag($0) } }.pickerStyle(.segmented).frame(width: 230)
            }.padding(30).padding(.bottom, 0)
            Group {
                switch mode {
                case .conversations: conversationView
                case .inbox: inbox
                case .contacts: contacts
                }
            }.transition(.opacity)
        }
        .animation(.easeOut(duration: 0.15), value: mode)
        .sheet(isPresented: $showingAddContact) { ContactEditorView(state: state) }
        .sheet(item: $editingRecord) { record in ContactEditorView(state: state, editing: record) }
        .confirmationDialog("کدام نسخهٔ مخاطب حذف شود؟", isPresented: Binding(get: { deletingContact != nil }, set: { if !$0 { deletingContact = nil } }), presenting: deletingContact) { contact in
            if contact.hasSIMRecord { Button("حذف از سیم‌کارت", role: .destructive) { Task { _ = await state.deleteContact(contact, storage: .sim); deletingContact = nil } } }
            if contact.hasModemRecord { Button("حذف از حافظه مودم", role: .destructive) { Task { _ = await state.deleteContact(contact, storage: .modem); deletingContact = nil } } }
            if contact.records.count > 1 { Button("حذف همه نسخه‌ها", role: .destructive) { Task { _ = await state.deleteContact(contact); deletingContact = nil } } }
        } message: { contact in Text("«\(contact.name)» ممکن است در چند حافظه ذخیره شده باشد.") }
    }

    private var conversationView: some View {
        HSplitView {
            List(state.conversations, selection: $selectedConversation) { conversation in
                HStack(spacing: 11) {
                    ZStack { Circle().fill(ModemTheme.blue.opacity(0.12)); Text(String(conversation.displayName.prefix(2))).font(.caption.bold()).foregroundStyle(ModemTheme.navy) }.frame(width: 38, height: 38)
                    VStack(alignment: .leading, spacing: 4) {
                        HStack { Text(conversation.displayName).fontWeight(conversation.unreadCount > 0 ? .bold : .medium); Spacer(); if conversation.unreadCount > 0 { Text("\(conversation.unreadCount)").font(.caption2.bold()).foregroundStyle(.white).padding(5).background(ModemTheme.blue, in: Circle()) } }
                        Text(conversation.lastMessage?.text ?? "").lineLimit(1).font(.callout).foregroundStyle(ModemTheme.muted)
                        Text(conversation.lastMessage?.displayTime ?? "").font(.caption2).foregroundStyle(ModemTheme.muted)
                    }
                }.padding(.vertical, 6).tag(conversation)
            }.scrollContentBackground(.hidden).frame(minWidth: 330)
            if let conversation = selectedConversation {
                VStack(spacing: 0) {
                    HStack { VStack(alignment: .leading) { Text(conversation.displayName).font(.title3.bold()); Text(conversation.peerNumber).font(.caption).foregroundStyle(ModemTheme.muted) }; Spacer(); if conversation.unreadCount > 0 { Button("خواندن همه") { Task { await state.markConversationRead(conversation) } } } }.padding(18).background(ModemTheme.surface)
                    ScrollViewReader { proxy in ScrollView { LazyVStack(spacing: 9) { ForEach(conversation.messages) { message in MessageBubble(message: message).id(message.id) } }.padding(18) }.onAppear { if let id = conversation.messages.last?.id { proxy.scrollTo(id, anchor: .bottom) } } }
                    HStack { TextField("پیام بنویسید…", text: $state.draft).textFieldStyle(ModemTextFieldStyle()); Button("ارسال") { state.recipient = conversation.peerNumber; Task { await state.sendMessage() } }.buttonStyle(NavyButtonStyle()).disabled(state.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || state.isSending) }.padding(14).background(ModemTheme.surface)
                }
            } else { ContentUnavailableView("یک گفتگو را انتخاب کنید", systemImage: "bubble.left.and.bubble.right") }
        }.padding(30).padding(.top, 10)
    }

    private var inbox: some View {
        HSplitView {
            VStack(spacing: 0) {
                List(state.messages, selection: $selected) { message in
                    HStack(alignment: .top, spacing: 11) {
                        ZStack { Circle().fill((message.isMissedCall ? ModemTheme.danger : ModemTheme.blue).opacity(0.12)); Image(systemName: message.isMissedCall ? "phone.arrow.down.left" : "message.fill").foregroundStyle(message.isMissedCall ? ModemTheme.danger : ModemTheme.blue) }.frame(width: 35, height: 35)
                        VStack(alignment: .leading, spacing: 5) { HStack { Text(message.displaySender).fontWeight(message.isUnread ? .bold : .medium); if message.isUnread { Circle().fill(ModemTheme.blue).frame(width: 7, height: 7) }; Spacer() }; Text(message.text).lineLimit(2).font(.callout).foregroundStyle(ModemTheme.muted); Text(message.displayTime).font(.caption2).foregroundStyle(ModemTheme.muted) }
                    }.padding(.vertical, 7).tag(message)
                }.scrollContentBackground(.hidden)
                ComposerView(state: state).padding(14)
            }.frame(minWidth: 355).background(ModemTheme.surface.opacity(0.7))
            MessageDetail(state: state, message: selected) { selected = nil }.frame(minWidth: 360)
        }.padding(30).padding(.top, 10)
    }

    private var contacts: some View {
        VStack(spacing: 16) {
            HStack {
                Image(systemName: "magnifyingglass").foregroundStyle(ModemTheme.muted)
                TextField("جستجو در نام یا شماره", text: $contactSearch).textFieldStyle(ModemTextFieldStyle())
                Picker("حافظه", selection: $contactStorageFilter) {
                    Text("همه (\(state.contacts.count))").tag(ContactStorage?.none)
                    Text("سیم‌کارت (\(state.contacts.filter(\.hasSIMRecord).count))").tag(ContactStorage?.some(.sim))
                    Text("مودم (\(state.contacts.filter(\.hasModemRecord).count))").tag(ContactStorage?.some(.modem))
                }.frame(width: 190)
                Button("افزودن مخاطب", systemImage: "person.badge.plus") { showingAddContact = true }.buttonStyle(NavyButtonStyle())
            }
            if filteredContacts.isEmpty {
                SoftCard { ContentUnavailableView(state.contacts.isEmpty ? "مخاطبی روی مودم نیست" : "مخاطبی پیدا نشد", systemImage: "person.crop.circle.badge.questionmark", description: Text(state.contacts.isEmpty ? "مخاطبین سیم‌کارت و حافظهٔ مودم اینجا نمایش داده می‌شوند." : "عبارت جستجو را تغییر دهید.")) }.frame(maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 260), spacing: 14)], spacing: 14) {
                        ForEach(filteredContacts) { contact in ContactCard(contact: contact, compose: { state.compose(to: contact); mode = .conversations }, edit: { editingRecord = contact.records.first }, delete: { deletingContact = contact }) }
                    }.padding(.vertical, 2)
                }
            }
        }.padding(30).padding(.top, 10)
    }
}

struct MessageBubble: View {
    let message: SMSMessage
    var body: some View {
        HStack {
            if message.direction == .incoming { Spacer(minLength: 80) }
            VStack(alignment: .leading, spacing: 5) {
                Text(message.text).textSelection(.enabled)
                HStack(spacing: 6) { Text(message.displayTime); Text(message.direction == .outgoing ? "ارسال‌شده" : message.storage) }.font(.caption2).foregroundStyle(message.direction == .outgoing ? Color.white.opacity(0.75) : ModemTheme.muted)
            }
            .foregroundStyle(message.direction == .outgoing ? Color.white : ModemTheme.ink)
            .padding(.horizontal, 13).padding(.vertical, 10)
            .background(message.direction == .outgoing ? ModemTheme.blue : ModemTheme.surface, in: RoundedRectangle(cornerRadius: 15, style: .continuous))
            .overlay { if message.direction == .incoming { RoundedRectangle(cornerRadius: 15).stroke(ModemTheme.line) } }
            if message.direction == .outgoing { Spacer(minLength: 80) }
        }
    }
}

struct ContactCard: View {
    let contact: ModemContact
    let compose: () -> Void
    let edit: () -> Void
    let delete: () -> Void
    var body: some View {
        SoftCard {
            HStack(spacing: 14) {
                ZStack {
                    Circle().fill(LinearGradient(colors: [ModemTheme.sky.opacity(0.3), ModemTheme.blue.opacity(0.18)], startPoint: .top, endPoint: .bottom))
                    Text(contact.initials).font(.system(size: 16, weight: .bold, design: .rounded)).foregroundStyle(ModemTheme.navy)
                }.frame(width: 48, height: 48)
                VStack(alignment: .leading, spacing: 4) {
                    Text(contact.name).font(.headline).lineLimit(1)
                    Text(contact.number.isEmpty ? "بدون شماره" : contact.number).font(.callout.monospacedDigit()).foregroundStyle(ModemTheme.muted).lineLimit(1)
                    HStack(spacing: 5) { Text(contact.group); Text("•"); Text(contact.storage) }.font(.caption2).foregroundStyle(ModemTheme.muted)
                }
                Spacer()
                VStack(spacing: 6) {
                    Button(action: compose) { Image(systemName: "message.fill").frame(width: 24, height: 24) }
                        .buttonStyle(.borderedProminent).tint(ModemTheme.blue).disabled(contact.number.isEmpty)
                        .help("ارسال پیام به \(contact.name)")
                    HStack(spacing: 5) {
                        Button(action: edit) { Image(systemName: "pencil").frame(width: 20, height: 20) }.buttonStyle(.borderless).foregroundStyle(ModemTheme.blue).help("ویرایش یا انتقال")
                        Button(action: delete) { Image(systemName: "trash").frame(width: 20, height: 20) }.buttonStyle(.borderless).foregroundStyle(ModemTheme.danger).help("حذف مخاطب")
                    }
                }
            }
        }
    }
}

struct ContactEditorView: View {
    let state: AppState
    let editing: ContactRecord?
    init(state: AppState, editing: ContactRecord? = nil) {
        self.state = state
        self.editing = editing
        _name = State(initialValue: editing?.name ?? "")
        _number = State(initialValue: editing?.number ?? "")
        _group = State(initialValue: editing?.group ?? .common)
        _storage = State(initialValue: editing?.storage ?? .modem)
    }
    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var number = ""
    @State private var group: ContactGroup = .common
    @State private var storage: ContactStorage = .modem
    @State private var saving = false

    private var isUnicode: Bool { name.unicodeScalars.contains { !$0.isASCII } }
    private var limit: Int { storage == .sim ? (isUnicode ? 14 : 20) : 30 }
    private var canSave: Bool { !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && !number.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty && name.count <= limit && !saving }

    var body: some View {
        VStack(alignment: .leading, spacing: 18) {
            HStack { VStack(alignment: .leading) { Text(editing == nil ? "افزودن مخاطب" : "ویرایش مخاطب").font(.title2.bold()); Text(editing == nil ? "محل ذخیره را خودتان انتخاب کنید." : "نسخهٔ جدید ابتدا ذخیره و تأیید میشود؛ سپس نسخهٔ قبلی حذف میگردد.").foregroundStyle(ModemTheme.muted) }; Spacer(); Button("بستن") { dismiss() } }
            TextField("نام و نام خانوادگی", text: $name).textFieldStyle(ModemTextFieldStyle())
            HStack { Text("\(name.count) از \(limit) کاراکتر").font(.caption).foregroundStyle(name.count > limit ? ModemTheme.danger : ModemTheme.muted); Spacer(); Text(storage.title).font(.caption.bold()).foregroundStyle(ModemTheme.blue) }
            TextField("شماره موبایل", text: $number).textFieldStyle(ModemTextFieldStyle())
            Picker("گروه", selection: $group) { ForEach(ContactGroup.allCases) { Text($0.title).tag($0) } }
            Picker("محل ذخیره", selection: $storage) { ForEach(ContactStorage.allCases) { Text($0.title).tag($0) } }.pickerStyle(.segmented)
            if storage == .sim { Label(isUnicode ? "نام فارسی روی سیم‌کارت حداکثر ۱۴ کاراکتر است." : "نام ASCII روی سیم‌کارت حداکثر ۲۰ کاراکتر است.", systemImage: "simcard").font(.caption).foregroundStyle(ModemTheme.muted) }
            HStack { Spacer(); Button(saving ? "در حال ذخیره…" : (editing == nil ? "ذخیره مخاطب" : "ذخیره تغییرات")) { saving = true; Task { let success: Bool; if let editing { success = await state.replaceContact(editing, name: name, number: number, group: group, storage: storage) } else { success = await state.addContact(name: name, number: number, group: group, storage: storage) }; saving = false; if success { dismiss() } } }.buttonStyle(NavyButtonStyle()).disabled(!canSave) }
        }.padding(26).frame(width: 470)
    }
}

struct MessageDetail: View {
    let state: AppState; let message: SMSMessage?; let clear: () -> Void
    var body: some View {
        if let message {
            SoftCard { VStack(alignment: .leading, spacing: 18) { HStack { VStack(alignment: .leading, spacing: 3) { Text(message.displaySender).font(.title2.bold()); Text(message.sender).font(.caption).foregroundStyle(ModemTheme.muted) }; Spacer(); if message.isMissedCall { Label("تماس ازدست‌رفته", systemImage: "phone.down.fill").foregroundStyle(ModemTheme.danger) } }; Divider(); Text(message.text).textSelection(.enabled).frame(maxWidth: .infinity, alignment: .leading); Spacer(); HStack { Text(message.displayTime).font(.caption).foregroundStyle(ModemTheme.muted); Spacer(); if message.isUnread { Button("خوانده شد") { Task { await state.markRead(message) } } }; Button("حذف", role: .destructive) { Task { await state.delete(message); clear() } } } }.padding(4) }
        } else { SoftCard { ContentUnavailableView("پیامی انتخاب نشده", systemImage: "bubble.left.and.bubble.right", description: Text("یک پیام را از فهرست انتخاب کنید.")) } }
    }
}

struct ComposerView: View {
    @Bindable var state: AppState
    var body: some View { SoftCard { VStack(alignment: .leading, spacing: 9) { Text("پیام جدید").font(.headline); TextField("شماره گیرنده", text: $state.recipient).textFieldStyle(ModemTextFieldStyle()); TextEditor(text: $state.draft).foregroundStyle(ModemTheme.ink).tint(ModemTheme.blue).frame(minHeight: 58).scrollContentBackground(.hidden).padding(6).background(Color.white, in: RoundedRectangle(cornerRadius: 10)).overlay(RoundedRectangle(cornerRadius: 10).stroke(ModemTheme.line)); HStack { Text("\(state.draft.count) نویسه").font(.caption).foregroundStyle(ModemTheme.muted); Spacer(); Button("ارسال") { Task { await state.sendMessage() } }.buttonStyle(NavyButtonStyle()).disabled(state.isSending || state.recipient.isEmpty || state.draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty) } } } }
}

struct USSDView: View {
    @Bindable var state: AppState
    @AppStorage("ussdPresets") private var presetsRaw = "*100#,*140*11#,*1#"
    private var presets: [String] { presetsRaw.split(separator: ",").map { $0.trimmingCharacters(in: .whitespaces) }.filter { !$0.isEmpty } }
    var body: some View {
        VStack(alignment: .leading, spacing: 22) {
            PageHeader(title: "کد دستوری", subtitle: "اعتبار، بستهٔ اینترنت و خدمات اپراتور")
            SoftCard {
                VStack(alignment: .leading, spacing: 16) {
                    Text("کد موردنظر را وارد کنید").font(.headline)
                    HStack {
                        TextField("*100#", text: $state.ussdCode).textFieldStyle(ModemTextFieldStyle()).font(.title3.monospaced())
                        Button("شماره‌گیری") { Task { await state.sendUSSD() } }.buttonStyle(NavyButtonStyle()).disabled(state.isSending || state.ussdCode.isEmpty)
                    }
                    HStack(spacing: 8) {
                        Text("پیشنهادها").font(.caption).foregroundStyle(ModemTheme.muted)
                        ForEach(presets, id: \.self) { code in Button(code) { state.ussdCode = code }.buttonStyle(.bordered) }
                    }
                }
            }
            SoftCard {
                VStack(alignment: .leading, spacing: 12) {
                    Label("پاسخ شبکه", systemImage: "antenna.radiowaves.left.and.right").font(.headline).foregroundStyle(ModemTheme.blue)
                    Text(state.ussdResponse.isEmpty ? "هنوز پاسخی دریافت نشده است." : state.ussdResponse)
                        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                        .textSelection(.enabled)
                        .foregroundStyle(state.ussdResponse.isEmpty ? ModemTheme.muted : ModemTheme.ink)
                }.frame(minHeight: 220)
            }
            Label("USSD یک نشست سیگنالینگ است، نه تماس صوتی. مودم‌های دیتا ممکن است پاسخ برخی کدها را از شبکه دریافت نکنند.", systemImage: "info.circle").font(.caption).foregroundStyle(ModemTheme.muted)
            Spacer()
        }.padding(30)
    }
}

struct DevicesView: View {
    let state: AppState
    @State private var filter = "all"
    @State private var search = ""
    @State private var confirmingReset = false

    private var filtered: [ConnectedDevice] {
        state.devices.filter { device in
            let statusOK = filter == "all" || (filter == "online" && device.isOnline) || (filter == "blocked" && device.isBlocked) || (filter == "history" && !device.isOnline && !device.isBlocked)
            let query = search.trimmingCharacters(in: .whitespaces)
            let queryOK = query.isEmpty || device.name.localizedCaseInsensitiveContains(query) || device.ip.contains(query) || device.mac.localizedCaseInsensitiveContains(query)
            return statusOK && queryOK
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            PageHeader(title: "دستگاه‌های شبکه", subtitle: "مدیریت اتصال و دسترسی کلاینت‌های مودم")
            HStack(spacing: 12) {
                TextField("جستجوی نام، IP یا MAC", text: $search).textFieldStyle(ModemTextFieldStyle())
                Picker("وضعیت", selection: $filter) {
                    Text("همه (\(state.devices.count))").tag("all")
                    Text("آنلاین (\(state.devices.filter(\.isOnline).count))").tag("online")
                    Text("مسدود (\(state.devices.filter(\.isBlocked).count))").tag("blocked")
                    Text("سابقه").tag("history")
                }.frame(width: 230)
                Button("صفر کردن ترافیک همه", systemImage: "arrow.counterclockwise") { confirmingReset = true }.disabled(state.devices.isEmpty)
            }
            SoftCard {
                Table(filtered) {
                    TableColumn("نام") { d in
                        HStack(spacing: 6) {
                            Image(systemName: d.isOnline ? "circle.fill" : d.isBlocked ? "nosign" : "circle").foregroundStyle(d.isOnline ? ModemTheme.success : d.isBlocked ? ModemTheme.danger : ModemTheme.muted).font(.caption)
                            Text(d.name).lineLimit(1)
                            if d.isCurrentMac { Text("این مک").font(.caption2.bold()).foregroundStyle(.white).padding(.horizontal, 6).padding(.vertical, 2).background(ModemTheme.blue, in: Capsule()) }
                        }
                    }
                    TableColumn("IP") { Text($0.ip).monospaced() }
                    TableColumn("MAC") { Text($0.mac).font(.caption.monospaced()) }
                    TableColumn("اتصال") { Text($0.connectionType).font(.caption) }
                    TableColumn("مدت") { Text(Formatters.duration($0.durationSeconds)).font(.caption) }
                    TableColumn("دریافت/ارسال") { Text("↓ \(Formatters.bytes($0.receivedBytes))  ↑ \(Formatters.bytes($0.sentBytes))").font(.caption) }
                    TableColumn("") { d in
                        Menu {
                            Button("قطع اتصال") { Task { await state.manage(d, action: "1") } }.disabled(d.isCurrentMac)
                            if d.isBlocked {
                                Button("رفع مسدودی") { Task { await state.manage(d, action: "3") } }
                            } else {
                                Button("مسدود کردن", role: .destructive) { Task { await state.manage(d, action: "2") } }.disabled(d.isCurrentMac)
                            }
                        } label: { Image(systemName: "ellipsis.circle") }
                    }
                }.frame(minHeight: 420)
            }
            if state.devices.contains(where: \.isCurrentMac) {
                Label("دستگاه «این مک» محافظت شده و از این اپ قطع یا مسدود نمی‌شود.", systemImage: "lock.shield").font(.caption).foregroundStyle(ModemTheme.muted)
            }
        }.padding(30)
        .confirmationDialog("ترافیک همهٔ دستگاه‌ها صفر شود؟", isPresented: $confirmingReset) {
            Button("صفر کردن ترافیک", role: .destructive) { Task { await state.resetTraffic() } }
        } message: { Text("این عملیات شمارندهٔ مصرف را برای همهٔ کلاینت‌ها بازنشانی می‌کند.") }
    }
}

struct NetworkView: View {
    @Bindable var state: AppState
    @State private var confirmApply = false
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                PageHeader(title: "شبکه و DNS", subtitle: "تنظیمات نام‌گذاری دامنه و محدودهٔ DHCP مودم")
                if let info = state.dnsInfo {
                    SoftCard {
                        VStack(alignment: .leading, spacing: 12) {
                            Label("وضعیت فعلی", systemImage: "network").font(.headline).foregroundStyle(ModemTheme.blue)
                            Grid(alignment: .leading, horizontalSpacing: 26, verticalSpacing: 8) {
                                GridRow { Text("DNS").foregroundStyle(ModemTheme.muted); Text(info.dnsEnabled ? "\(info.dns1)\(info.dns2.isEmpty ? "" : " • \(info.dns2)")" : "خودکار (اپراتور/مودم)") }
                                GridRow { Text("مودم").foregroundStyle(ModemTheme.muted); Text(info.ip.isEmpty ? "--" : info.ip).monospaced() }
                                GridRow { Text("محدودهٔ DHCP").foregroundStyle(ModemTheme.muted); Text("\(info.start) – \(info.end)").monospaced() }
                                GridRow { Text("مدت اجاره").foregroundStyle(ModemTheme.muted); Text(info.leaseTime.isEmpty ? "--" : "\(info.leaseTime)") }
                            }.font(.callout)
                        }
                    }
                } else {
                    SoftCard { HStack { ProgressView(); Text("در حال خواندن تنظیمات شبکه…").foregroundStyle(ModemTheme.muted) }.frame(maxWidth: .infinity, minHeight: 90) }
                }
                SoftCard {
                    VStack(alignment: .leading, spacing: 14) {
                        Label("پروفایل DNS", systemImage: "shield.lefthalf.filled").font(.headline).foregroundStyle(ModemTheme.blue)
                        ForEach(DNSProfile.allCases) { profile in
                            Button { state.dnsProfile = profile } label: {
                                HStack {
                                    Image(systemName: state.dnsProfile == profile ? "largecircle.fill.circle" : "circle").foregroundStyle(ModemTheme.blue)
                                    VStack(alignment: .leading, spacing: 2) { Text(profile.title).fontWeight(.medium); Text(profile.detail).font(.caption).foregroundStyle(ModemTheme.muted) }
                                    Spacer()
                                    if !profile.primary.isEmpty { Text(profile.primary).font(.caption.monospaced()).foregroundStyle(ModemTheme.muted) }
                                }.padding(10).background(state.dnsProfile == profile ? ModemTheme.blue.opacity(0.08) : Color.clear, in: RoundedRectangle(cornerRadius: 10))
                            }.buttonStyle(.plain)
                        }
                        if state.dnsProfile == .custom {
                            HStack { TextField("DNS اول", text: $state.customDNS1).textFieldStyle(ModemTextFieldStyle()); TextField("DNS دوم (اختیاری)", text: $state.customDNS2).textFieldStyle(ModemTextFieldStyle()) }
                        }
                        HStack { Spacer(); Button("اعمال تنظیمات DNS") { confirmApply = true }.buttonStyle(NavyButtonStyle()).disabled(state.isSending) }
                    }
                }
                Label("تغییر DNS اتصال اینترنت را برای چند ثانیه قطع می‌کند. محدودهٔ DHCP دست‌نخورده می‌ماند.", systemImage: "exclamationmark.triangle").font(.caption).foregroundStyle(ModemTheme.warning)
            }.padding(30)
        }
        .task { if state.dnsInfo == nil { await state.loadDNS() } }
        .confirmationDialog("تنظیمات DNS اعمال شود؟", isPresented: $confirmApply) {
            Button("اعمال", role: .destructive) { Task { _ = await state.applyDNS() } }
        } message: { Text("اتصال شبکه ممکن است چند لحظه قطع شود.") }
    }
}

struct FileShareView: View {
    @Bindable var server: FileShareServer
    @State private var isTargeted = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                PageHeader(title: "اشتراک فایل", subtitle: "ارسال مستقیم فایل به دستگاه‌های متصل به Wi-Fi مودم")
                if let file = server.sharedFile, server.state == .running {
                    activeShare(file)
                } else {
                    dropZone
                }
                securityNote
            }.padding(30)
        }
        .onDrop(of: [.fileURL], isTargeted: $isTargeted) { providers in
            guard let provider = providers.first else { return false }
            provider.loadDataRepresentation(forTypeIdentifier: "public.file-url") { data, _ in
                guard let data, let url = URL(dataRepresentation: data, relativeTo: nil) else { return }
                Task { @MainActor in server.share(url: url) }
            }
            return true
        }
    }

    private var dropZone: some View {
        VStack(spacing: 18) {
            ZStack { Circle().fill(ModemTheme.blue.opacity(0.12)).frame(width: 88, height: 88); Image(systemName: "arrow.up.doc.fill").font(.system(size: 34)).foregroundStyle(ModemTheme.blue) }
            VStack(spacing: 7) { Text("فایل را اینجا رها کنید").font(.system(size: 22, weight: .bold, design: .rounded)); Text("یا از Finder یک فایل انتخاب کنید").foregroundStyle(ModemTheme.muted) }
            Picker("مدت اشتراک", selection: $server.expirationMinutes) { Text("۱۵ دقیقه").tag(15); Text("۱ ساعت").tag(60); Text("۴ ساعت").tag(240) }.pickerStyle(.segmented).frame(maxWidth: 380)
            Button("انتخاب فایل") { server.chooseFile() }.buttonStyle(NavyButtonStyle())
            if case .failed(let message) = server.state { Label(message, systemImage: "exclamationmark.triangle.fill").foregroundStyle(ModemTheme.danger) }
        }
        .frame(maxWidth: .infinity, minHeight: 350)
        .background(isTargeted ? ModemTheme.blue.opacity(0.12) : ModemTheme.surface, in: RoundedRectangle(cornerRadius: 24, style: .continuous))
        .overlay(RoundedRectangle(cornerRadius: 24, style: .continuous).stroke(style: StrokeStyle(lineWidth: 2, dash: [8])).foregroundStyle(isTargeted ? ModemTheme.blue : ModemTheme.line))
        .animation(.easeOut(duration: 0.12), value: isTargeted)
    }

    private func activeShare(_ file: SharedFile) -> some View {
        HStack(alignment: .top, spacing: 22) {
            SoftCard {
                VStack(alignment: .leading, spacing: 18) {
                    HStack(spacing: 14) { ZStack { RoundedRectangle(cornerRadius: 14).fill(ModemTheme.blue.opacity(0.12)); Image(systemName: "doc.fill").font(.title2).foregroundStyle(ModemTheme.blue) }.frame(width: 52, height: 52); VStack(alignment: .leading, spacing: 3) { Text(file.name).font(.headline).lineLimit(2); Text(Formatters.bytes(file.size)).foregroundStyle(ModemTheme.muted) }; Spacer() }
                    Divider()
                    VStack(alignment: .leading, spacing: 7) { Text("لینک دانلود").font(.caption).foregroundStyle(ModemTheme.muted); Text(server.downloadURL?.absoluteString ?? "در حال راه‌اندازی…").font(.callout.monospaced()).textSelection(.enabled).foregroundStyle(ModemTheme.ink) }
                    HStack { Button("کپی لینک") { server.copyLink() }.buttonStyle(NavyButtonStyle()); if let url = server.downloadURL { ShareLink(item: url) { Label("اشتراک لینک", systemImage: "square.and.arrow.up") } }; Spacer(); Button("توقف اشتراک", role: .destructive) { server.stop() } }
                    HStack(spacing: 20) { Label("\(server.downloadCount) دانلود", systemImage: "arrow.down.circle"); Label("انقضا \(file.expiresAt.formatted(date: .omitted, time: .shortened))", systemImage: "timer") }.font(.caption).foregroundStyle(ModemTheme.muted)
                }
            }
            SoftCard {
                VStack(spacing: 12) {
                    if let image = server.qrImage() { Image(nsImage: image).interpolation(.none).resizable().frame(width: 190, height: 190).accessibilityLabel("بارکد لینک دانلود") }
                    Text("با دوربین موبایل اسکن کنید").font(.headline)
                    Text("هر دو دستگاه باید به Wi-Fi مودم متصل باشند.").font(.caption).foregroundStyle(ModemTheme.muted).multilineTextAlignment(.center)
                }.frame(width: 220)
            }
        }
    }

    private var securityNote: some View {
        HStack(alignment: .top, spacing: 12) { Image(systemName: "lock.shield.fill").foregroundStyle(ModemTheme.success); VStack(alignment: .leading, spacing: 4) { Text("اشتراک امن در شبکهٔ محلی").font(.headline); Text("لینک با توکن تصادفی ساخته می‌شود، فهرست فایل عمومی وجود ندارد، مسیر واقعی فایل مخفی است و اشتراک در زمان انتخاب‌شده منقضی می‌شود.").font(.callout).foregroundStyle(ModemTheme.muted) } }.padding(18).background(ModemTheme.success.opacity(0.08), in: RoundedRectangle(cornerRadius: 16))
    }
}

struct SettingsView: View {
    @Bindable var state: AppState
    @State private var rebootConfirmation = false
    private var panelURL: URL? { URL(string: "http://\(state.host)") }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                PageHeader(title: "تنظیمات", subtitle: "اتصال، رفتار برنامه و اطلاعات نسخه")
                SoftCard {
                    VStack(alignment: .leading, spacing: 15) {
                        Label("اتصال به مودم", systemImage: "network").font(.headline).foregroundStyle(ModemTheme.blue)
                        TextField("آدرس IP مودم", text: $state.host).textFieldStyle(ModemTextFieldStyle())
                        Text("فقط IPv4 خصوصی LAN پذیرفته می‌شود؛ پیش‌فرض 192.168.1.1.").font(.caption).foregroundStyle(ModemTheme.muted)
                        Button("آزمایش اتصال") { Task { await state.refresh() } }.buttonStyle(NavyButtonStyle())
                    }
                }
                SoftCard {
                    VStack(alignment: .leading, spacing: 14) {
                        Label("مدیریت مودم", systemImage: "wifi.router").font(.headline).foregroundStyle(ModemTheme.blue)
                        if let panelURL { Link("باز کردن پنل مدیریت", destination: panelURL) }
                        Button("راه‌اندازی مجدد مودم", role: .destructive) { rebootConfirmation = true }.disabled(state.rebootPhase.isBusy)
                        HStack(spacing: 8) {
                            if state.rebootPhase.isBusy { ProgressView().controlSize(.small) }
                            Text(state.rebootPhase.title).font(.caption).foregroundStyle(state.rebootPhase == .timedOut ? ModemTheme.danger : ModemTheme.muted)
                        }
                    }
                }
                SoftCard {
                    VStack(alignment: .leading, spacing: 10) {
                        Label("درباره", systemImage: "info.circle").font(.headline).foregroundStyle(ModemTheme.blue)
                        LabeledContent("نسخه", value: "2.3.0")
                        LabeledContent("پیاده‌سازی", value: "Swift 6 + SwiftUI")
                        Text("نسخهٔ بومی، مستقل و بدون Python یا وب‌سرور. تماس سیم‌کارتی توسط این مودم پشتیبانی نمی‌شود؛ تشخیص تماس ازدست‌رفته بر پایهٔ پیامک اپراتور است.").font(.caption).foregroundStyle(ModemTheme.muted)
                    }
                }
            }.padding(30)
        }
        .confirmationDialog("مودم راه‌اندازی مجدد شود؟", isPresented: $rebootConfirmation) {
            Button("راه‌اندازی مجدد", role: .destructive) { Task { await state.reboot() } }
        } message: { Text("اتصال چند دقیقه قطع می‌شود؛ برنامه تلاش می‌کند بازگشت مودم را تشخیص دهد.") }
    }
}

struct PageHeader: View {
    let title: String; let subtitle: String
    var body: some View { HStack(alignment: .center) { VStack(alignment: .leading, spacing: 5) { Text(title).font(.system(size: 29, weight: .bold, design: .rounded)).foregroundStyle(ModemTheme.ink); Text(subtitle).foregroundStyle(ModemTheme.muted) }; Spacer() } }
}

struct OfflineState: View {
    var body: some View { SoftCard { ContentUnavailableView("مودم در دسترس نیست", systemImage: "wifi.slash", description: Text("به Wi-Fi مودم متصل شوید یا آدرس را در تنظیمات بررسی کنید.")) }.frame(minHeight: 320) }
}
