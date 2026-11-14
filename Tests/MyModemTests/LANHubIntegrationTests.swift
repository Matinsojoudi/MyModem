import Foundation
import Testing
@testable import MyModemApp

@MainActor
struct LANHubIntegrationTests {
    @Test func pairingThenUploadListAndClipboardOverHTTP() async throws {
        let directory = FileManager.default.temporaryDirectory.appending(path: "mymodem-hub-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }

        let hub = LANHub()
        hub.start()
        defer { hub.stop() }
        for _ in 0..<50 where hub.baseURL == nil { try await Task.sleep(for: .milliseconds(100)) }
        let base = try #require(hub.baseURL)

        let code = hub.auth.beginPairing()
        var pairRequest = URLRequest(url: base.appending(path: "api/pair"))
        pairRequest.httpMethod = "POST"
        pairRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        pairRequest.httpBody = try JSONSerialization.data(withJSONObject: ["code": code.code, "name": "TestPhone"])
        let (pairData, pairResponse) = try await URLSession.shared.data(for: pairRequest)
        #expect((pairResponse as? HTTPURLResponse)?.statusCode == 200)
        let token = try #require((try JSONSerialization.jsonObject(with: pairData) as? [String: Any])?["token"] as? String)

        // Unauthorized listing must fail.
        let (_, unauthorized) = try await URLSession.shared.data(from: base.appending(path: "api/files"))
        #expect((unauthorized as? HTTPURLResponse)?.statusCode == 401)

        // Authorized upload.
        let payload = Data("hello from phone".utf8)
        var upload = URLRequest(url: base.appending(path: "api/upload"))
        upload.httpMethod = "POST"
        upload.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        upload.setValue("note.txt".addingPercentEncoding(withAllowedCharacters: .alphanumerics), forHTTPHeaderField: "X-Filename")
        upload.httpBody = payload
        let (uploadData, uploadResponse) = try await URLSession.shared.data(for: upload)
        #expect((uploadResponse as? HTTPURLResponse)?.statusCode == 200, "upload failed: \(String(decoding: uploadData, as: UTF8.self))")
        let fileID = try #require((try JSONSerialization.jsonObject(with: uploadData) as? [String: Any])?["id"] as? String)

        // Authorized listing now contains it.
        var list = URLRequest(url: base.appending(path: "api/files"))
        list.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (listData, _) = try await URLSession.shared.data(for: list)
        let files = (try JSONSerialization.jsonObject(with: listData) as? [String: Any])?["files"] as? [[String: Any]] ?? []
        #expect(files.contains { $0["id"] as? String == fileID })

        // Download returns exact bytes.
        var download = URLRequest(url: base.appending(path: "f/\(fileID)"))
        download.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (downloaded, downloadResponse) = try await URLSession.shared.data(for: download)
        #expect((downloadResponse as? HTTPURLResponse)?.statusCode == 200)
        #expect(downloaded == payload)

        // Clipboard round-trip.
        var clip = URLRequest(url: base.appending(path: "api/clipboard"))
        clip.httpMethod = "POST"
        clip.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        clip.setValue("application/json", forHTTPHeaderField: "Content-Type")
        clip.httpBody = try JSONSerialization.data(withJSONObject: ["text": "متن مشترک"])
        _ = try await URLSession.shared.data(for: clip)
        var clipGet = URLRequest(url: base.appending(path: "api/clipboard"))
        clipGet.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        let (clipData, _) = try await URLSession.shared.data(for: clipGet)
        #expect((try JSONSerialization.jsonObject(with: clipData) as? [String: Any])?["text"] as? String == "متن مشترک")

        hub.library.removeAll()
    }
}
