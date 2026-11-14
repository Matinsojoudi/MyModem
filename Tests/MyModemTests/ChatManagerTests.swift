import Foundation
import Testing
@testable import MyModemApp

@MainActor
struct ChatManagerTests {
    private func isolated() throws -> (ChatManager, URL) {
        let directory = FileManager.default.temporaryDirectory.appending(path: "mymodem-chat-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return (ChatManager(baseDirectory: directory), directory)
    }

    @Test func createsAndPersistsRoom() throws {
        let (chat, directory) = try isolated()
        defer { try? FileManager.default.removeItem(at: directory) }
        let room = chat.createRoom(title: "  خانواده  ")
        #expect(room.title == "خانواده")
        let reloaded = ChatManager(baseDirectory: directory)
        #expect(reloaded.rooms.first?.id == room.id)
    }

    @Test func postsMessageAndRejectsEmpty() throws {
        let (chat, directory) = try isolated()
        defer { try? FileManager.default.removeItem(at: directory) }
        let room = chat.createRoom(title: "تست")
        #expect(chat.post(roomID: room.id, senderID: "a", senderName: "علی", text: "   ") == nil)
        #expect(chat.post(roomID: room.id, senderID: "a", senderName: "علی", text: "سلام") != nil)
        #expect(chat.room(id: room.id)?.messages.count == 1)
    }

    @Test func truncatesOverlongMessages() throws {
        let (chat, directory) = try isolated()
        defer { try? FileManager.default.removeItem(at: directory) }
        let room = chat.createRoom(title: "تست")
        let long = String(repeating: "x", count: ChatManager.maxMessageLength + 100)
        let message = try #require(chat.post(roomID: room.id, senderID: "a", senderName: "a", text: long))
        #expect(message.text.count == ChatManager.maxMessageLength)
    }

    @Test func capsMessageHistory() throws {
        let (chat, directory) = try isolated()
        defer { try? FileManager.default.removeItem(at: directory) }
        let room = chat.createRoom(title: "تست")
        for index in 0..<(ChatManager.maxMessagesPerRoom + 25) {
            chat.post(roomID: room.id, senderID: "a", senderName: "a", text: "m\(index)")
        }
        #expect(chat.room(id: room.id)?.messages.count == ChatManager.maxMessagesPerRoom)
    }

    @Test func signalsAreScopedToRecipientAndRoom() throws {
        let (chat, directory) = try isolated()
        defer { try? FileManager.default.removeItem(at: directory) }
        let room = chat.createRoom(title: "تست")
        let other = chat.createRoom(title: "دیگر")
        chat.addSignal(roomID: room.id, from: "a", to: "b", type: "offer", payload: "{}")
        chat.addSignal(roomID: room.id, from: "a", to: "c", type: "offer", payload: "{}")
        chat.addSignal(roomID: other.id, from: "a", to: "b", type: "offer", payload: "{}")
        #expect(chat.signals(for: room.id, recipient: "b", after: nil).count == 1)
        #expect(chat.signals(for: room.id, recipient: "z", after: nil).isEmpty)
    }

    @Test func deletingRoomRemovesItsSignals() throws {
        let (chat, directory) = try isolated()
        defer { try? FileManager.default.removeItem(at: directory) }
        let room = chat.createRoom(title: "تست")
        chat.addSignal(roomID: room.id, from: "a", to: "b", type: "offer", payload: "{}")
        chat.deleteRoom(room)
        #expect(chat.room(id: room.id) == nil)
        #expect(chat.signals(for: room.id, recipient: "b", after: nil).isEmpty)
    }

    @Test func presenceExpiresStaleParticipants() throws {
        let (chat, directory) = try isolated()
        defer { try? FileManager.default.removeItem(at: directory) }
        chat.touch(participant: "a", name: "علی")
        #expect(chat.participants().count == 1)
    }
}
