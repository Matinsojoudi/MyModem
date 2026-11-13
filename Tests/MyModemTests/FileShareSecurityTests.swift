import Foundation
import Testing
@testable import MyModemApp

struct FileShareSecurityTests {
    @Test func generatedTokensAreOpaqueAndUnique() {
        let first = FileShareServer.randomToken()
        let second = FileShareServer.randomToken()
        #expect(first.count == 32)
        let isHex = first.allSatisfy { $0.isHexDigit }
        #expect(isHex)
        #expect(first != second)
    }

    @Test @MainActor func servesExactFileAndRejectsWrongToken() async throws {
        let expected = Data("MyModem secure LAN transfer".utf8)
        let file = FileManager.default.temporaryDirectory.appending(path: "mymodem-share-test.txt")
        try expected.write(to: file, options: .atomic)
        defer { try? FileManager.default.removeItem(at: file) }

        let server = FileShareServer()
        server.share(url: file)
        defer { server.stop() }
        for _ in 0..<50 where server.downloadURL == nil {
            try await Task.sleep(for: .milliseconds(100))
        }
        let url = try #require(server.downloadURL)
        let (data, response) = try await URLSession.shared.data(from: url)
        #expect((response as? HTTPURLResponse)?.statusCode == 200)
        #expect(data == expected)

        let wrongURL = url.deletingLastPathComponent().appending(path: "wrong-token")
        let (_, wrongResponse) = try await URLSession.shared.data(from: wrongURL)
        #expect((wrongResponse as? HTTPURLResponse)?.statusCode == 404)
    }

    @Test func tokenComparisonRejectsLengthAndContentMismatch() {
        let token = "0123456789abcdef0123456789abcdef"
        #expect(FileShareServer.constantTimeEquals(token, token))
        #expect(!FileShareServer.constantTimeEquals(token, token + "00"))
        #expect(!FileShareServer.constantTimeEquals(token, "1123456789abcdef0123456789abcdef"))
    }
}
