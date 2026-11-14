import Foundation

actor ModemClient {
    private let codec = ModemCodec()
    private let dateFormatter = JalaliDateFormatter()
    private var host: ModemHost
    private let session: URLSession

    init(host: String = "192.168.1.1") {
        self.host = (try? ModemHost(host)) ?? (try! ModemHost("192.168.1.1"))
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 5
        configuration.timeoutIntervalForResource = 12
        session = URLSession(configuration: configuration)
    }

    func updateHost(_ host: String) throws { self.host = try ModemHost(host) }

    func status() async throws -> ModemStatus {
        ModemStatus(json: try await get(file: "json_status_info"))
    }

    func messages() async throws -> [SMSMessage] {
        let local = try await post(file: "json_message_set", payload: ["message_flag": "GET_RCV_SMS_LOCAL", "page_number": 1, "data_per_page": "50"])
        let sim = try await post(file: "json_message_set", payload: ["message_flag": "GET_SIM_SMS", "page_number": 1, "data_per_page": "50"])
        let responses = [local, sim]
        var seen = Set<String>()
        return responses.flatMap { $0["message_list"] as? [[String: Any]] ?? [] }
            .compactMap { raw -> SMSMessage? in
                let id = raw["index"] as? String ?? ""
                guard !id.isEmpty, seen.insert(id).inserted else { return nil }
                let sender = codec.decode(raw["from"] as? String ?? "").trimmingCharacters(in: CharacterSet(charactersIn: ";"))
                let text = codec.decode(raw["subject"] as? String ?? "")
                let rawTime = raw["received"] as? String ?? ""
                let missed = text.localizedCaseInsensitiveContains("missed call") || text.contains("تماس از دست رفته") || text.contains("تماس ازدست رفته")
                return SMSMessage(id: id, sender: sender, senderName: "", text: text, rawTime: rawTime, displayTime: dateFormatter.string(fromModemTimestamp: rawTime), isUnread: String(describing: raw["status"] ?? "1") == "0", isMissedCall: missed, callerNumber: extractPhone(text), storage: id.contains("SRCV") ? "سیم‌کارت" : "دستگاه")
            }
            .sorted { $0.rawTime > $1.rawTime }
    }

    func contacts() async throws -> [ModemContact] {
        let response = try await post(file: "json_pb_set", payload: [
            "pb_action": "pb_get_all", "location": "2", "page_num": "1", "data_per_page": "100"
        ])
        let entries = response["pb_entries"] as? [[String: Any]] ?? []
        var contactsByNumber: [String: ModemContact] = [:]
        var contactsWithoutNumber: [ModemContact] = []

        for entry in entries {
            guard let identifier = entry["pbm_id"] as? String, !identifier.isEmpty else { continue }
            let decoded = codec.decode(entry["pbm_name"] as? String ?? "")
            let parts = splitContactHeader(decoded)
            let rawNumber = (entry["pbm_number"] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            let number = rawNumber.isEmpty ? parts.number : rawNumber
            let normalized = codec.normalizePhone(number)
            let name = parts.name.isEmpty ? (decoded.isEmpty ? "بی‌نام" : decoded.replacingOccurrences(of: ";", with: " ").trimmingCharacters(in: .whitespaces)) : parts.name
            let location = String(describing: entry["pbm_location"] ?? "1")
            let groupCode = entry["pbm_group"] as? String ?? "common"
            let group = ["common": "عمومی", "family": "خانواده", "friend": "دوستان", "colleague": "همکاران"][groupCode] ?? groupCode
            let contact = ModemContact(id: identifier, allIDs: [identifier], name: name.isEmpty ? "بی‌نام" : name, number: number, normalizedNumber: normalized, group: group, storage: location == "0" ? "سیم‌کارت" : "دستگاه")

            guard !normalized.isEmpty else { contactsWithoutNumber.append(contact); continue }
            if let existing = contactsByNumber[normalized] {
                let preferred = existing.name == "بی‌نام" || contact.name.count > existing.name.count ? contact : existing
                contactsByNumber[normalized] = ModemContact(id: preferred.id, allIDs: Array(Set(existing.allIDs + contact.allIDs)).sorted(), name: preferred.name, number: preferred.number, normalizedNumber: normalized, group: preferred.group, storage: preferred.storage)
            } else {
                contactsByNumber[normalized] = contact
            }
        }

        return (Array(contactsByNumber.values) + contactsWithoutNumber).sorted {
            $0.name.localizedStandardCompare($1.name) == .orderedAscending
        }
    }

    func sendSMS(to phone: String, text: String) async throws {
        let numbers = phone.split(whereSeparator: { $0 == "," || $0 == ";" }).map { codec.normalizePhone(String($0)) }.filter { !$0.isEmpty }
        guard !numbers.isEmpty, !text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else { throw ModemError.modemRejected }
        let result = try await post(file: "json_message_set", payload: [
            "send_from_draft_id": "", "message_flag": "SEND_SMS", "sms_cmd": "4",
            "contacts": numbers.joined(separator: ",") + ",", "content": codec.encode(text),
            "encode_type": "UNICODE", "sms_time": modemTime()
        ])
        guard String(describing: result["sms_cmd_status_result"] ?? "") == "3" else { throw ModemError.modemRejected }
    }

    func markRead(_ message: SMSMessage) async throws {
        let isSIM = message.id.contains("SRCV")
        let result = try await post(file: "json_message_set", payload: ["message_flag": "SET_MSG_READ", "sms_cmd": "7", "tags": isSIM ? "" : "12", "mem_store": isSIM ? "0" : "1", "read_message_id": message.id.hasSuffix(",") ? message.id : message.id + ","])
        guard String(describing: result["sms_cmd_status_result"] ?? "") == "3" else { throw ModemError.modemRejected }
    }

    func delete(_ message: SMSMessage) async throws {
        let isSIM = message.id.contains("SRCV")
        let result = try await post(file: "json_message_set", payload: ["message_flag": "DELETE_SMS", "sms_cmd": "6", "tags": isSIM ? "" : "12", "mem_store": isSIM ? "0" : "1", "delete_message_id": message.id.hasSuffix(",") ? message.id : message.id + ","])
        guard String(describing: result["sms_cmd_status_result"] ?? "") == "3" else { throw ModemError.modemRejected }
    }

    func sendUSSD(_ rawCode: String) async throws -> String {
        var code = rawCode.trimmingCharacters(in: .whitespacesAndNewlines)
        if !code.hasPrefix("*") { code = "*" + code }
        if !code.hasSuffix("#") { code += "#" }
        _ = try? await post(file: "json_ussd_set", payload: ["action": "2", "ussd_param": ""])
        try await Task.sleep(for: .milliseconds(400))
        _ = try await post(file: "json_ussd_set", payload: ["action": "1", "ussd_param": code])
        for _ in 0..<6 {
            try await Task.sleep(for: .seconds(1))
            let response = try await get(file: "json_ussd_info")
            let text = codec.decode(response["ussd_str"] as? String ?? "")
            if !text.isEmpty { return text }
            let type = String(describing: response["ussd_type"] ?? "")
            if type == "2" { return "نشست USSD توسط شبکه بسته شد." }
            if type == "3" { return "نشست USSD توسط ارتباط دیگری پاسخ داده شد." }
            if type == "4" { return "این کد توسط اپراتور پشتیبانی نمی‌شود." }
        }
        return "زمان انتظار برای پاسخ شبکه تمام شد."
    }

    func devices() async throws -> [ConnectedDevice] {
        let response = try await get(file: "json_device_management_info")
        return (response["client_list"] as? [[String: Any]] ?? []).compactMap { raw in
            let mac = raw["m"] as? String ?? ""
            guard !mac.isEmpty else { return nil }
            let state = String(describing: raw["s"] ?? "0")
            let name = decodeUTF8Hex(raw["n"] as? String ?? "")
            return ConnectedDevice(id: raw["i"] as? String ?? mac, name: name.isEmpty ? "دستگاه بی‌نام" : name, mac: mac, ip: raw["ip"] as? String ?? "--", status: state, isOnline: state == "1", isBlocked: state == "2", receivedBytes: safeCounter(raw["rx"]), sentBytes: safeCounter(raw["tx"]))
        }.sorted { ($0.isOnline ? 0 : $0.isBlocked ? 1 : 2) < ($1.isOnline ? 0 : $1.isBlocked ? 1 : 2) }
    }

    func manageDevice(_ device: ConnectedDevice, action: String) async throws {
        let result = try await post(file: "json_device_management_set", payload: ["action": action, "mac": device.mac])
        guard result["result"] as? String == "success" else { throw ModemError.modemRejected }
    }

    func reboot() async throws { _ = try await get(file: "json_device_restart") }

    private func get(file: String) async throws -> [String: Any] { try await request(file: file, method: "get", payload: nil) }
    private func post(file: String, payload: [String: Any]) async throws -> [String: Any] { try await request(file: file, method: "post", payload: payload) }

    private func request(file: String, method: String, payload: [String: Any]?) async throws -> [String: Any] {
        var components = URLComponents(string: "http://\(host.value)/xml_action.cgi")
        components?.queryItems = [.init(name: "method", value: method), .init(name: "module", value: "duster"), .init(name: "file", value: file + String(Int(Date().timeIntervalSince1970 * 1000)))]
        guard let url = components?.url else { throw ModemError.invalidAddress }
        var request = URLRequest(url: url)
        request.httpMethod = method == "post" ? "POST" : "GET"
        if let payload { request.httpBody = try JSONSerialization.data(withJSONObject: payload); request.setValue("application/json", forHTTPHeaderField: "Content-Type") }
        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else { throw ModemError.invalidResponse }
            guard http.statusCode == 200 else { throw ModemError.server(http.statusCode) }
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else { throw ModemError.invalidResponse }
            return json
        } catch let error as ModemError { throw error }
        catch { throw ModemError.unavailable(error.localizedDescription) }
    }

    private func modemTime() -> String { let formatter = DateFormatter(); formatter.timeZone = TimeZone(identifier: "Asia/Tehran"); formatter.dateFormat = "yy,MM,dd,HH,mm,ss,+3.5"; return formatter.string(from: Date()) }
    private func splitContactHeader(_ input: String) -> (name: String, number: String) {
        let values = input.split(separator: ";", omittingEmptySubsequences: true).map { String($0).trimmingCharacters(in: .whitespaces) }
        var nameParts: [String] = []
        var number = ""
        for value in values {
            let compact = value.filter { $0.isNumber || $0 == "+" }
            if compact.count >= 3, compact.count >= value.count - 2 { number = value }
            else { nameParts.append(value) }
        }
        return (nameParts.joined(separator: " "), number)
    }
    private func extractPhone(_ text: String) -> String { text.split(whereSeparator: \ .isWhitespace).map(String.init).first { $0.hasPrefix("+98") || $0.hasPrefix("09") } ?? "" }
    private func decodeUTF8Hex(_ input: String) -> String { var bytes: [UInt8] = []; var i = input.startIndex; while let end = input.index(i, offsetBy: 2, limitedBy: input.endIndex), i < input.endIndex { if let byte = UInt8(input[i..<end], radix: 16) { bytes.append(byte) }; i = end }; return String(decoding: bytes, as: UTF8.self).trimmingCharacters(in: .whitespacesAndNewlines) }
    private func safeCounter(_ value: Any?) -> Int64 { let parsed = Int64(String(describing: value ?? "0")) ?? 0; return parsed < 0 || parsed > 10 * 1_099_511_627_776 ? 0 : parsed }
}
