import AppKit
import SwiftUI

struct TransferView: View {
    @Bindable var hub: LANHub
    @State private var clipboardDraft = ""
    @State private var confirmRevokeAll = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                PageHeader(title: "کتابخانه و کلیپ‌بورد", subtitle: "انتقال امن فایل و متن بین مک و دستگاه‌های متصل به Wi‑Fi مودم")
                serverCard
                pairingCard
                libraryCard
                clipboardCard
            }.padding(30)
        }
        .task { if hub.clipboard.text.isEmpty == false, clipboardDraft.isEmpty { clipboardDraft = hub.clipboard.text } }
    }

    private var serverCard: some View {
        SoftCard {
            HStack(spacing: 16) {
                ZStack { Circle().fill((hub.state == .running ? ModemTheme.success : ModemTheme.muted).opacity(0.15)); Image(systemName: "wifi.router").foregroundStyle(hub.state == .running ? ModemTheme.success : ModemTheme.muted) }.frame(width: 46, height: 46)
                VStack(alignment: .leading, spacing: 3) {
                    Text(hub.state == .running ? "سرور انتقال فعال است" : "سرور انتقال خاموش است").font(.headline)
                    if let url = hub.baseURL, hub.state == .running { Text(url.absoluteString).font(.caption.monospaced()).textSelection(.enabled).foregroundStyle(ModemTheme.muted) }
                    else { Text("برای دریافت فایل و متن از موبایل، ابتدا سرور را روشن کنید.").font(.caption).foregroundStyle(ModemTheme.muted) }
                }
                Spacer()
                if hub.state == .running { Button("خاموش کردن", role: .destructive) { hub.stop() } }
                else { Button("روشن کردن سرور") { hub.start() }.buttonStyle(NavyButtonStyle()) }
            }
        }
    }

    private var pairingCard: some View {
        SoftCard {
            VStack(alignment: .leading, spacing: 14) {
                Label("اتصال دستگاه جدید", systemImage: "qrcode").font(.headline).foregroundStyle(ModemTheme.blue)
                Text("کد یک‌بارمصرف بسازید و QR را با دوربین موبایل اسکن کنید. هر کد فقط یک‌بار و تا ۵ دقیقه معتبر است.").font(.callout).foregroundStyle(ModemTheme.muted)
                HStack(alignment: .top, spacing: 20) {
                    VStack(alignment: .leading, spacing: 10) {
                        if let code = hub.pairingCode, !code.isExpired {
                            Text(code.code).font(.system(size: 34, weight: .bold, design: .monospaced)).tracking(8).textSelection(.enabled)
                            Text("انقضا: \(code.expiresAt.formatted(date: .omitted, time: .shortened))").font(.caption).foregroundStyle(ModemTheme.muted)
                        } else {
                            Text("کدی فعال نیست").foregroundStyle(ModemTheme.muted)
                        }
                        HStack {
                            Button(hub.pairingCode == nil ? "ساخت کد اتصال" : "کد تازه") { hub.makePairingCode() }.buttonStyle(NavyButtonStyle()).disabled(hub.state != .running)
                            if hub.pairingCode != nil { Button("لغو") { hub.cancelPairing() } }
                        }
                        if hub.state != .running { Text("ابتدا سرور را روشن کنید.").font(.caption).foregroundStyle(ModemTheme.warning) }
                    }
                    Spacer()
                    if let image = hub.qrImage() { Image(nsImage: image).interpolation(.none).resizable().frame(width: 150, height: 150).accessibilityLabel("بارکد اتصال دستگاه") }
                }
                Divider()
                HStack {
                    Text("دستگاه‌های متصل (\(hub.auth.pairedDevices.count))").font(.subheadline.bold())
                    Spacer()
                    if !hub.auth.pairedDevices.isEmpty { Button("لغو همه", role: .destructive) { confirmRevokeAll = true } }
                }
                if hub.auth.pairedDevices.isEmpty {
                    Text("هنوز دستگاهی متصل نشده است.").font(.caption).foregroundStyle(ModemTheme.muted)
                } else {
                    ForEach(hub.auth.pairedDevices) { device in
                        HStack {
                            Image(systemName: "iphone").foregroundStyle(ModemTheme.blue)
                            Text(device.name).lineLimit(1)
                            Spacer()
                            Text(device.lastSeen.formatted(date: .abbreviated, time: .shortened)).font(.caption).foregroundStyle(ModemTheme.muted)
                            Button("قطع دسترسی", role: .destructive) { hub.auth.revoke(device) }
                        }.padding(8).background(ModemTheme.canvas.opacity(0.6), in: RoundedRectangle(cornerRadius: 9))
                    }
                }
            }
        }
        .confirmationDialog("دسترسی همهٔ دستگاه‌ها لغو شود؟", isPresented: $confirmRevokeAll) {
            Button("لغو همه", role: .destructive) { hub.auth.revokeAll() }
        }
    }

    private var libraryCard: some View {
        SoftCard {
            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    Label("کتابخانهٔ فایل", systemImage: "folder").font(.headline).foregroundStyle(ModemTheme.blue)
                    Spacer()
                    Text(Formatters.bytes(hub.library.totalSize)).font(.caption).foregroundStyle(ModemTheme.muted)
                    Button("افزودن فایل", systemImage: "plus") { hub.addFiles() }
                }
                if hub.library.files.isEmpty {
                    Text("فایلی در کتابخانه نیست. فایل‌ها پس از افزودن روی دیسک می‌مانند و با کد اتصال قابل دانلودند.").font(.caption).foregroundStyle(ModemTheme.muted)
                } else {
                    ForEach(hub.library.files) { file in
                        HStack(spacing: 10) {
                            Image(systemName: "doc.fill").foregroundStyle(ModemTheme.blue)
                            VStack(alignment: .leading, spacing: 2) {
                                Text(file.fileName).lineLimit(1)
                                Text("\(Formatters.bytes(file.size)) • \(file.downloads) دانلود").font(.caption2).foregroundStyle(ModemTheme.muted)
                            }
                            Spacer()
                            Button { hub.copyURL(for: file) } label: { Image(systemName: "link") }.help("کپی لینک")
                            Button(role: .destructive) { hub.library.remove(file) } label: { Image(systemName: "trash") }
                        }.padding(8).background(ModemTheme.canvas.opacity(0.5), in: RoundedRectangle(cornerRadius: 9))
                    }
                }
            }
        }
    }

    private var clipboardCard: some View {
        SoftCard {
            VStack(alignment: .leading, spacing: 10) {
                Label("کلیپ‌بورد مشترک", systemImage: "doc.on.clipboard").font(.headline).foregroundStyle(ModemTheme.blue)
                Text("متنی که اینجا می‌گذارید در صفحهٔ دستگاه‌های متصل دیده می‌شود؛ حداکثر ۶۴ کیلوبایت.").font(.caption).foregroundStyle(ModemTheme.muted)
                TextEditor(text: $clipboardDraft)
                    .foregroundStyle(ModemTheme.ink).tint(ModemTheme.blue)
                    .frame(minHeight: 90).scrollContentBackground(.hidden).padding(6)
                    .background(Color.white, in: RoundedRectangle(cornerRadius: 10))
                    .overlay(RoundedRectangle(cornerRadius: 10).stroke(ModemTheme.line))
                HStack {
                    if let updated = hub.clipboard.updatedAt { Text("آخرین تغییر: \(updated.formatted(date: .omitted, time: .shortened))").font(.caption).foregroundStyle(ModemTheme.muted) }
                    Spacer()
                    Button("پاک کردن") { clipboardDraft = ""; hub.clipboard.clear() }
                    Button("ذخیره") { _ = hub.clipboard.update(clipboardDraft) }.buttonStyle(NavyButtonStyle())
                    Button("خواندن از مک") { clipboardDraft = hub.clipboard.text }
                }
            }
        }
    }
}
