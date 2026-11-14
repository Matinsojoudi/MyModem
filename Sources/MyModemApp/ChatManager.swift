import Foundation
import Observation

struct ChatMessage: Codable, Identifiable, Sendable, Hashable {
    let id: String
    let roomID: String
    let senderID: String
    let senderName: String
    let text: String
    let createdAt: Date
    let isSystem: Bool
}

struct ChatSignal: Codable, Sendable, Hashable {
    let id: String
    let roomID: String
    let fromID: String
    let toID: String
    let type: String
    let payload: String
    let createdAt: Date
}

struct ChatRoom: Codable, Identifiable, Sendable, Hashable {
    let id: String
    var title: String
    let createdAt: Date
    var messages: [ChatMessage]
}

@MainActor
@Observable
final class ChatManager {
    static let maxMessagesPerRoom = 200
    static let maxMessageLength = 4_000

    private(set) var rooms: [ChatRoom] = []
    private var signals: [ChatSignal] = []
    private var presence: [String: (name: String, seen: Date)] = [:]
    private let storeURL: URL

    init(baseDirectory: URL? = nil) {
        let base = baseDirectory ?? FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0].appending(path: "MyModem", directoryHint: .isDirectory)
        try? FileManager.default.createDirectory(at: base, withIntermediateDirectories: true)
        storeURL = base.appending(path: "chat.json")
        load()
    }

    func createRoom(title: String) -> ChatRoom {
        let clean = title.trimmingCharacters(in: .whitespacesAndNewlines)
        let room = ChatRoom(id: Self.randomID(), title: clean.isEmpty ? "اتاق گفتگوی LAN" : String(clean.prefix(60)), createdAt: Date(), messages: [])
        rooms.insert(room, at: 0)
        save()
        return room
    }

    func deleteRoom(_ room: ChatRoom) {
        rooms.removeAll { $0.id == room.id }
        signals.removeAll { $0.roomID == room.id }
        save()
    }

    func room(id: String) -> ChatRoom? { rooms.first { $0.id == id } }

    @discardableResult
    func post(roomID: String, senderID: String, senderName: String, text: String) -> ChatMessage? {
        guard let index = rooms.firstIndex(where: { $0.id == roomID }) else { return nil }
        let clean = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !clean.isEmpty else { return nil }
        let message = ChatMessage(id: Self.randomID(), roomID: roomID, senderID: senderID, senderName: senderName.isEmpty ? "مهمان" : senderName, text: String(clean.prefix(Self.maxMessageLength)), createdAt: Date(), isSystem: false)
        rooms[index].messages.append(message)
        if rooms[index].messages.count > Self.maxMessagesPerRoom {
            rooms[index].messages.removeFirst(rooms[index].messages.count - Self.maxMessagesPerRoom)
        }
        save()
        return message
    }

    func messages(in roomID: String, after: Date?) -> [ChatMessage] {
        guard let room = room(id: roomID) else { return [] }
        guard let after else { return room.messages }
        return room.messages.filter { $0.createdAt > after }
    }

    func touch(participant id: String, name: String) {
        presence[id] = (name, Date())
        presence = presence.filter { Date().timeIntervalSince($0.value.seen) < 60 }
    }

    func participants() -> [(id: String, name: String)] {
        presence.filter { Date().timeIntervalSince($0.value.seen) < 60 }
            .map { (id: $0.key, name: $0.value.name) }
            .sorted { $0.name < $1.name }
    }

    func addSignal(roomID: String, from: String, to: String, type: String, payload: String) {
        guard room(id: roomID) != nil else { return }
        signals.append(ChatSignal(id: Self.randomID(), roomID: roomID, fromID: from, toID: to, type: String(type.prefix(20)), payload: String(payload.prefix(8_000)), createdAt: Date()))
        if signals.count > 400 { signals.removeFirst(signals.count - 400) }
    }

    func signals(for roomID: String, recipient: String, after: Date?) -> [ChatSignal] {
        signals.filter { signal in
            signal.roomID == roomID && (signal.toID == recipient || signal.toID == "*")
                && (after.map { signal.createdAt > $0 } ?? true)
        }
    }

    private func load() {
        guard let data = try? Data(contentsOf: storeURL),
              let value = try? JSONDecoder().decode([ChatRoom].self, from: data) else { return }
        rooms = value
    }

    private func save() {
        if let data = try? JSONEncoder().encode(rooms) {
            try? data.write(to: storeURL, options: .atomic)
        }
    }

    nonisolated static func randomID() -> String {
        UUID().uuidString.replacingOccurrences(of: "-", with: "").lowercased().prefix(16).description
    }
}
