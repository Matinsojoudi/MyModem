import AppKit
import SwiftUI

struct ChatView: View {
    @Bindable var hub: LANHub
    @State private var selectedRoom: ChatRoom?
    @State private var draft = ""
    @State private var newRoomTitle = ""
    @State private var showingNewRoom = false

    private var room: ChatRoom? { selectedRoom.flatMap { hub.chat.room(id: $0.id) } }

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            HStack {
                PageHeader(title: "گفتگوی شبکهٔ محلی", subtitle: "متن و تماس صوتی/تصویری بین دستگاه‌های همین Wi‑Fi")
                Spacer()
                Button("اتاق جدید", systemImage: "plus.bubble") { showingNewRoom = true }.disabled(hub.state != .running)
            }
            Text("تماس صوتی/تصویری داخل همین Wi‑Fi انجام می‌شود و صدای مک/موبایل را جابه‌جا می‌کند؛ تماس با شمارهٔ سیم‌کارت پشتیبانی نمی‌شود.")
                .font(.caption).foregroundStyle(ModemTheme.muted)
            if hub.state != .running {
                Label("برای استفاده از چت، سرور انتقال را در بخش «کتابخانه و کلیپ‌بورد» روشن کنید.", systemImage: "exclamationmark.triangle").font(.callout).foregroundStyle(ModemTheme.warning)
            }
            HSplitView {
                VStack(spacing: 0) {
                    List(hub.chat.rooms, selection: $selectedRoom) { item in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(item.title).fontWeight(.medium).lineLimit(1)
                            Text("\(item.messages.count) پیام").font(.caption2).foregroundStyle(ModemTheme.muted)
                        }.padding(.vertical, 5).tag(item)
                    }.scrollContentBackground(.hidden)
                }.frame(minWidth: 240)
                Group {
                    if let room {
                        transcript(room)
                    } else {
                        ContentUnavailableView("اتاقی انتخاب نشده", systemImage: "bubble.left.and.bubble.right", description: Text("یک اتاق بسازید یا از فهرست انتخاب کنید."))
                    }
                }.frame(minWidth: 420)
            }
        }
        .padding(30)
        .sheet(isPresented: $showingNewRoom) {
            VStack(alignment: .leading, spacing: 16) {
                Text("اتاق جدید").font(.title3.bold())
                TextField("نام اتاق", text: $newRoomTitle).textFieldStyle(ModemTextFieldStyle())
                HStack {
                    Spacer()
                    Button("انصراف") { showingNewRoom = false }
                    Button("ساخت") {
                        let room = hub.chat.createRoom(title: newRoomTitle)
                        selectedRoom = room
                        newRoomTitle = ""
                        showingNewRoom = false
                    }.buttonStyle(NavyButtonStyle())
                }
            }.padding(24).frame(width: 420)
        }
    }

    private func transcript(_ room: ChatRoom) -> some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text(room.title).font(.headline)
                    Text("\(room.messages.count) پیام • \(hub.chat.participants().count) حاضر").font(.caption).foregroundStyle(ModemTheme.muted)
                }
                Spacer()
                if let link = roomLink(room) {
                    Button("تماس صوتی/تصویری", systemImage: "video.fill") { NSWorkspace.shared.open(link) }
                        .help("صفحهٔ اتاق در مرورگر باز می‌شود؛ میکروفون و دوربین همان‌جا استفاده می‌شوند.")
                    Button { NSWorkspace.shared.open(link) } label: { Image(systemName: "safari") }.accessibilityLabel("باز کردن اتاق در مرورگر")
                }
                Button(role: .destructive) { hub.chat.deleteRoom(room); selectedRoom = nil } label: { Image(systemName: "trash") }.accessibilityLabel("حذف اتاق \(room.title)")
            }.padding(14).background(ModemTheme.surface)

            ScrollView {
                LazyVStack(alignment: .leading, spacing: 8) {
                    ForEach(room.messages) { message in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(message.senderName).font(.caption2).foregroundStyle(ModemTheme.muted)
                            Text(message.text).textSelection(.enabled)
                            Text(message.createdAt.formatted(date: .omitted, time: .shortened)).font(.caption2).foregroundStyle(ModemTheme.muted)
                        }
                        .padding(10)
                        .background(message.senderName == hostName ? ModemTheme.blue.opacity(0.12) : Color.white, in: RoundedRectangle(cornerRadius: 12))
                        .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }.padding(14)
            }
            HStack {
                TextField("پیام…", text: $draft).textFieldStyle(ModemTextFieldStyle())
                Button("ارسال") {
                    _ = hub.chat.post(roomID: room.id, senderID: "host", senderName: hostName, text: draft)
                    draft = ""
                }.buttonStyle(NavyButtonStyle()).disabled(draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
            }.padding(12).background(ModemTheme.surface)
        }
    }

    private var hostName: String { Host.current().localizedName ?? "مک" }

    private func roomLink(_ room: ChatRoom) -> URL? {
        hub.baseURL.flatMap { URL(string: $0.absoluteString + "/chat?room=" + room.id) }
    }
}
