import Foundation
import Testing
@testable import MyModemApp

@MainActor
struct LANHubTests {
    private func isolatedAuth() throws -> (LANAuth, URL) {
        let directory = FileManager.default.temporaryDirectory.appending(path: "mymodem-auth-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return (LANAuth(baseDirectory: directory), directory)
    }

    @Test func pairingCodeIsSingleUse() throws {
        let (auth, directory) = try isolatedAuth()
        defer { try? FileManager.default.removeItem(at: directory) }
        let code = auth.beginPairing()
        #expect(auth.redeem(code: code.code, deviceName: "iPhone") != nil)
        #expect(auth.redeem(code: code.code, deviceName: "iPhone") == nil)
    }

    @Test func wrongPairingCodeIsRejected() throws {
        let (auth, directory) = try isolatedAuth()
        defer { try? FileManager.default.removeItem(at: directory) }
        let code = auth.beginPairing()
        let wrong = code.code == "000000" ? "111111" : "000000"
        #expect(auth.redeem(code: wrong, deviceName: "x") == nil)
        #expect(auth.pairedDevices.isEmpty)
    }

    @Test func pairedTokenAuthorizesAndRevocationWorks() throws {
        let (auth, directory) = try isolatedAuth()
        defer { try? FileManager.default.removeItem(at: directory) }
        let token = try #require(auth.redeem(code: auth.beginPairing().code, deviceName: "iPhone"))
        #expect(auth.authorize(token: token)?.name == "iPhone")
        #expect(auth.authorize(token: "deadbeef") == nil)
        let device = try #require(auth.pairedDevices.first)
        auth.revoke(device)
        #expect(auth.authorize(token: token) == nil)
    }

    @Test func tokensAreHashedNotStoredRaw() throws {
        let (auth, directory) = try isolatedAuth()
        defer { try? FileManager.default.removeItem(at: directory) }
        let token = try #require(auth.redeem(code: auth.beginPairing().code, deviceName: "iPad"))
        let device = try #require(auth.pairedDevices.first)
        #expect(device.tokenHash != token)
        #expect(device.tokenHash == LANAuth.hash(token))
    }

    @Test func pairingStopsAfterFiveFailures() throws {
        let (auth, directory) = try isolatedAuth()
        defer { try? FileManager.default.removeItem(at: directory) }
        let code = auth.beginPairing()
        let wrong = code.code == "000000" ? "111111" : "000000"
        for _ in 0..<5 { #expect(auth.redeem(code: wrong, deviceName: "x") == nil) }
        #expect(auth.redeem(code: code.code, deviceName: "x") == nil)
    }

    @Test func rangeParsingHandlesSuffixAndClamping() {
        #expect(LANHub.parseRange("bytes=0-99", size: 1000) == 0...99)
        #expect(LANHub.parseRange("bytes=900-", size: 1000) == 900...999)
        #expect(LANHub.parseRange("bytes=-100", size: 1000) == 900...999)
        #expect(LANHub.parseRange("bytes=500-2000", size: 1000) == 500...999)
        #expect(LANHub.parseRange("bytes=1000-2000", size: 1000) == nil)
        #expect(LANHub.parseRange("items=0-1", size: 1000) == nil)
        #expect(LANHub.parseRange("bytes=0-0", size: 0) == nil)
    }

    @Test func clipboardCapsOversizedText() throws {
        let directory = FileManager.default.temporaryDirectory.appending(path: "mymodem-clip-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let store = ClipboardStore(baseDirectory: directory)
        let huge = String(repeating: "ا", count: ClipboardStore.maxLength + 500)
        #expect(!store.update(huge))
        #expect(store.text.count == ClipboardStore.maxLength)
        store.clear()
        #expect(store.text.isEmpty)
    }

    @Test func libraryStripsTraversalFromStoredNames() {
        #expect(!FileLibrary.sanitizedName("../../etc/passwd").contains("/"))
        #expect(FileLibrary.sanitizedName("").isEmpty == false)
        #expect(!FileLibrary.sanitizedName("a b:c?.txt").contains(":"))
    }
}
