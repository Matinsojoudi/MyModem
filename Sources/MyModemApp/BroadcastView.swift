import AppKit
import SwiftUI
import UniformTypeIdentifiers

struct BroadcastView: View {
    @Bindable var state: AppState
    @State private var confirmStart = false
    @State private var showReport = false

    private var engine: BroadcastEngine { state.broadcast }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                PageHeader(title: "پیام همگانی", subtitle: "ارسال پیام شخصی‌سازی‌شده با متغیرهای فایل CSV")
                warning
                importCard
                if let list = engine.list {
                    variablesCard(list)
                    templateCard(list)
                    runCard(list)
                }
            }.padding(30)
        }
        .confirmationDialog("ارسال واقعی پیامک آغاز شود؟", isPresented: $confirmStart) {
            Button("ارسال به \(engine.total) نفر", role: .destructive) { state.startBroadcast() }
        } message: {
            Text("این عملیات پیامک واقعی از سیم‌کارت مودم ارسال می‌کند و ممکن است هزینه یا محدودیت اپراتور داشته باشد.")
        }
        .sheet(isPresented: $showReport) { reportSheet }
    }

    private var warning: some View {
        HStack(alignment: .top, spacing: 10) {
            Image(systemName: "exclamationmark.shield.fill").foregroundStyle(ModemTheme.warning)
            VStack(alignment: .leading, spacing: 3) {
                Text("قبل از ارسال، برای چند شمارهٔ آزمایشی بفرست.").font(.subheadline.bold())
                Text("هر ردیف یک پیامک جدا می‌گیرد؛ بین پیام‌ها فاصله زمانی رعایت می‌شود تا مودم و اپراتور دچار محدودیت نشوند. ارسال خودکار دوباره انجام نمی‌شود.")
                    .font(.caption).foregroundStyle(ModemTheme.muted)
            }
        }.padding(14).background(ModemTheme.warning.opacity(0.09), in: RoundedRectangle(cornerRadius: 14))
    }

    private var importCard: some View {
        SoftCard {
            VStack(alignment: .leading, spacing: 12) {
                Label("فایل گیرندگان", systemImage: "doc.badge.plus").font(.headline).foregroundStyle(ModemTheme.blue)
                Text("فایل CSV با ستون موبایل (مثلاً «موبایل» یا mobile). بقیهٔ ستون‌ها به‌صورت متغیر قابل استفاده‌اند.").font(.callout).foregroundStyle(ModemTheme.muted)
                HStack(spacing: 12) {
                    Button("انتخاب فایل CSV") { pickFile() }.buttonStyle(NavyButtonStyle())
                    if let list = engine.list {
                        Label("\(list.rows.count) گیرنده", systemImage: "person.2.fill").font(.callout)
                        Text("ستون شماره: \(list.phoneColumn)").font(.caption).foregroundStyle(ModemTheme.muted)
                        Button("پاک کردن") { engine.reset() }
                    }
                }
                if let error = engine.lastError {
                    Label(error, systemImage: "exclamationmark.triangle.fill").font(.caption).foregroundStyle(ModemTheme.danger)
                }
            }
        }
    }

    private func variablesCard(_ list: RecipientList) -> some View {
        SoftCard {
            VStack(alignment: .leading, spacing: 10) {
                Label("متغیرها", systemImage: "curlybraces").font(.headline).foregroundStyle(ModemTheme.blue)
                Text("روی هر متغیر بزن تا در متن درج شود.").font(.caption).foregroundStyle(ModemTheme.muted)
                FlowChips(items: list.headers + ["نام کامل", "موبایل"]) { key in
                    engine.template += "{{\(key)}}"
                }
                if !engine.missingVariables.isEmpty {
                    Label("این متغیرها در فایل نیستند: \(engine.missingVariables.joined(separator: "، "))", systemImage: "questionmark.circle")
                        .font(.caption).foregroundStyle(ModemTheme.warning)
                }
                Divider()
                if let first = list.rows.first {
                    Grid(alignment: .leading, horizontalSpacing: 20, verticalSpacing: 6) {
                        GridRow { Text("نمونه").foregroundStyle(ModemTheme.muted); Text(first.displayName) }
                        GridRow { Text("شماره").foregroundStyle(ModemTheme.muted); Text(first.phone).monospaced() }
                    }.font(.callout)
                }
            }
        }
    }

    private func templateCard(_ list: RecipientList) -> some View {
        SoftCard {
            VStack(alignment: .leading, spacing: 10) {
                Label("متن پیام", systemImage: "text.bubble").font(.headline).foregroundStyle(ModemTheme.blue)
                TextEditor(text: Binding(get: { engine.template }, set: { engine.template = $0 }))
                    .font(.body)
                    .frame(minHeight: 110)
                    .scrollContentBackground(.hidden)
                    .padding(8)
                    .background(Color.white, in: RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(ModemTheme.line))
                HStack {
                    Text("\(engine.template.count) نویسه").font(.caption).foregroundStyle(ModemTheme.muted)
                    Spacer()
                    Text("مثال: \(TemplateRenderer.preview(engine.template, row: list.rows.first, limit: 90))")
                        .font(.caption).foregroundStyle(ModemTheme.muted).lineLimit(2)
                }
            }
        }
    }

    private func runCard(_ list: RecipientList) -> some View {
        SoftCard {
            VStack(alignment: .leading, spacing: 14) {
                HStack {
                    Label("اجرای ارسال", systemImage: "paperplane").font(.headline).foregroundStyle(ModemTheme.blue)
                    Spacer()
                    Text("\(engine.sent) موفق • \(engine.failed) ناموفق • \(engine.processed)/\(engine.total)")
                        .font(.caption).foregroundStyle(ModemTheme.muted)
                }
                ProgressView(value: engine.progress).tint(ModemTheme.blue)
                HStack(spacing: 16) {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("فاصلهٔ بین پیام‌ها: \(engine.delaySeconds, specifier: "%.1f") ثانیه").font(.caption)
                        Slider(value: Binding(get: { engine.delaySeconds }, set: { engine.delaySeconds = $0 }), in: 1.5...10, step: 0.5).frame(width: 240)
                    }
                    Spacer()
                    if engine.isRunning {
                        Button("توقف", role: .destructive) { engine.stop() }
                    } else {
                        Button("شروع ارسال") { confirmStart = true }
                            .buttonStyle(NavyButtonStyle())
                            .disabled(engine.total == 0 || engine.template.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || state.isSending)
                    }
                    Button("گزارش") { showReport = true }.disabled(engine.report.isEmpty)
                }
                Text("وضعیت: \(phaseTitle)").font(.caption).foregroundStyle(ModemTheme.muted)
                if let error = engine.lastError, !engine.isRunning {
                    Text(error).font(.caption).foregroundStyle(ModemTheme.danger)
                }
            }
        }
    }

    private var phaseTitle: String {
        switch engine.phase {
        case .idle: "آماده"
        case .running: "در حال ارسال"
        case .paused: "متوقف شده"
        case .finished: "پایان یافت"
        case .stopped: "با توقف کاربر متوقف شد"
        }
    }

    private var reportSheet: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Text("گزارش ارسال").font(.title3.bold())
                Spacer()
                Button("بستن") { showReport = false }
            }
            Table(engine.report) {
                TableColumn("نام") { Text($0.name).lineLimit(1) }
                TableColumn("شماره") { Text($0.phone).monospaced() }
                TableColumn("وضعیت") { row in
                    Text(row.status).foregroundStyle(row.status == "ارسال شد" ? ModemTheme.success : row.status == "ناموفق" ? ModemTheme.danger : ModemTheme.muted)
                }
            }.frame(minHeight: 380)
            HStack {
                Spacer()
                Button("خروجی CSV گزارش") { exportReport() }
            }
        }.padding(22).frame(width: 720, height: 560)
    }

    private func pickFile() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.commaSeparatedText, .plainText, .text]
        panel.allowsMultipleSelection = false
        guard panel.runModal() == .OK, let url = panel.url else { return }
        engine.load(url: url)
    }

    private func exportReport() {
        let panel = NSSavePanel()
        panel.nameFieldStringValue = "broadcast-report.csv"
        guard panel.runModal() == .OK, let url = panel.url else { return }
        try? Data(engine.reportCSV().utf8).write(to: url, options: .atomic)
    }
}

struct FlowChips: View {
    let items: [String]
    let action: (String) -> Void
    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 110), spacing: 8)], alignment: .leading, spacing: 8) {
            ForEach(items, id: \.self) { item in
                Button { action(item) } label: {
                    Text("{{\(item)}}")
                        .font(.caption.monospaced())
                        .padding(.horizontal, 10).padding(.vertical, 5)
                        .background(ModemTheme.blue.opacity(0.1), in: Capsule())
                        .foregroundStyle(ModemTheme.blue)
                }.buttonStyle(.plain)
            }
        }
    }
}
