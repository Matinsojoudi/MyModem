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
                return SMSMessage(id: id, sender: sender, senderName: "", text: text, rawTime: rawTime, displayTime: dateFormatter.string(fromModemTimestamp: rawTime), isUnread: String(describing: raw["status"] ?? "1") == "0", isMissedCall: missed, callerNumber: extractPhone(text), storage: id.contains("SRCV") ? "سیم‌کارت" : "دستگاه", direction: .incoming)
            }
            .sorted { $0.rawTime > $1.rawTime }
    }

    func contacts() async throws -> [ModemContact] {
        let response = try await post(file: "json_pb_set", payload: [
            "pb_action": "pb_get_all", "location": "2", "page_num": "1", "data_per_page": "100"
        ])
        let entries = response["pb_entries"] as? [[String: Any]] ?? []
        var records: [ContactRecord] = []
        for entry in entries {
            guard let identifier = entry["pbm_id"] as? String, !identifier.isEmpty else { continue }
            let decoded = codec.decode(entry["pbm_name"] as? String ?? "")
            let parts = splitContactHeader(decoded)
            let rawNumber = (entry["pbm_number"] as? String ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            let number = rawNumber.isEmpty ? parts.number : rawNumber
            let normalized = codec.normalizePhone(number)
            let name = parts.name.isEmpty ? (decoded.isEmpty ? "بی‌نام" : decoded.replacingOccurrences(of: ";", with: " ").trimmingCharacters(in: .whitespaces)) : parts.name
            let storage = ContactStorage(rawValue: String(describing: entry["pbm_location"] ?? "1")) ?? .modem
            let group = ContactGroup(rawValue: entry["pbm_group"] as? String ?? "common") ?? .common
            records.append(.init(id: identifier, name: name.isEmpty ? "بی‌نام" : name, number: number, normalizedNumber: normalized, group: group, storage: storage))
        }

        let grouped = Dictionary(grouping: records) { record in
            record.normalizedNumber.isEmpty ? "id:\(record.id)" : record.normalizedNumber
        }
        return grouped.values.map { records in
            let preferred = records.max { left, right in
                let leftScore = left.name == "بی‌نام" ? 0 : left.name.count
                let rightScore = right.name == "بی‌نام" ? 0 : right.name.count
                return leftScore < rightScore
            } ?? records[0]
            return ModemContact(normalizedNumber: preferred.normalizedNumber, preferredName: preferred.name, records: records.sorted { $0.storage.rawValue < $1.storage.rawValue })
        }.sorted { $0.name.localizedStandardCompare($1.name) == .orderedAscending }
    }

    func sentMessages() async throws -> [SMSMessage] {
        let response = try await post(file: "json_message_set", payload: ["message_flag": "GET_SENT_SMS_LOCAL", "page_number": 1, "data_per_page": "50"])
        return (response["message_list"] as? [[String: Any]] ?? []).compactMap { raw in
            let id = raw["index"] as? String ?? ""
            guard !id.isEmpty else { return nil }
            let header = codec.decode(raw["from"] as? String ?? "").trimmingCharacters(in: CharacterSet(charactersIn: ";"))
            let parts = splitContactHeader(header)
            let recipient = parts.number.isEmpty ? header : parts.number
            let text = codec.decode(raw["subject"] as? String ?? "")
            let rawTime = raw["received"] as? String ?? ""
            return SMSMessage(id: id, sender: recipient, senderName: parts.name, text: text, rawTime: rawTime, displayTime: dateFormatter.string(fromModemTimestamp: rawTime), isUnread: false, isMissedCall: false, callerNumber: "", storage: "دستگاه", direction: .outgoing)
        }.sorted { $0.rawTime > $1.rawTime }
    }

    func addContact(name: String, number: String, group: ContactGroup, storage: ContactStorage) async throws {
        let cleanName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let cleanNumber = codec.normalizePhone(number)
        guard !cleanName.isEmpty, !cleanNumber.isEmpty else { throw ModemError.modemRejected }
        let isUnicode = cleanName.unicodeScalars.contains { !$0.isASCII }
        let maxLength = storage == .sim ? (isUnicode ? 14 : 20) : 30
        guard cleanName.count <= maxLength else { throw ModemError.contactNameTooLong(maxLength) }
        let result = try await post(file: "json_pb_set", payload: [
            "pb_action": "pbm_contact_add", "location": storage.rawValue,
            "name": codec.encode(cleanName), "mobile": cleanNumber, "group": group.rawValue
        ])
        guard String(describing: result["pb_result"] ?? "") == "0" else { throw ModemError.modemRejected }
    }

    func deleteContactRecords(ids: [String]) async throws {
        let cleanIDs = ids.filter { !$0.isEmpty }
        guard !cleanIDs.isEmpty else { throw ModemError.modemRejected }
        let result = try await post(file: "json_pb_set", payload: [
            "pb_action": "pbm_contact_delete", "location": "2", "delete_option": "delete_num",
            "delete_pb_id": cleanIDs.map { $0.hasSuffix(",") ? $0 : $0 + "," }.joined()
        ])
        guard String(describing: result["pb_result"] ?? "") == "0" else { throw ModemError.modemRejected }
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

    func markRead(_ messages: [SMSMessage]) async -> Int {
        var count = 0
        for message in messages where message.direction == .incoming && message.isUnread {
            if (try? await markRead(message)) != nil { count += 1 }
        }
        return count
    }

    func delete(_ message: SMSMessage) async throws {
        let isSIM = message.id.contains("SRCV")
        let result = try await post(file: "json_message_set", payload: ["message_flag": "DELETE_SMS", "sms_cmd": "6", "tags": isSIM ? "" : "12", "mem_store": isSIM ? "0" : "1", "delete_message_id": message.id.hasSuffix(",") ? message.id : message.id + ","])
        guard String(describing: result["sms_cmd_status_result"] ?? "") == "3" else { throw ModemError.modemRejected }
    }

    func sendUSSD(_ rawCode: String) async -> USSDState {
        var code = rawCode.trimmingCharacters(in: .whitespacesAndNewlines)
        if !code.hasPrefix("*") { code = "*" + code }
        if !code.hasSuffix("#") { code += "#" }
        _ = try? await post(file: "json_ussd_set", payload: ["action": "2", "ussd_param": ""])
        try? await Task.sleep(for: .milliseconds(400))
        do { _ = try await post(file: "json_ussd_set", payload: ["action": "1", "ussd_param": code]) }
        catch { return .transport(error.localizedDescription) }
        for _ in 0..<8 {
            try? await Task.sleep(for: .seconds(1))
            guard let response = try? await get(file: "json_ussd_info") else { continue }
            let text = codec.decode(response["ussd_str"] as? String ?? "")
            if !text.isEmpty { return .message(text) }
            switch String(describing: response["ussd_type"] ?? "") {
            case "2": return .terminated
            case "3": return .answeredElsewhere
            case "4": return .unsupported
            case "0", "1": return .empty
            default: continue
            }
        }
        return .timedOut
    }

    func devices() async throws -> [ConnectedDevice] {
        let response = try await get(file: "json_device_management_info")
        return (response["client_list"] as? [[String: Any]] ?? []).compactMap { raw in
            let mac = raw["m"] as? String ?? ""
            guard !mac.isEmpty else { return nil }
            let state = String(describing: raw["s"] ?? "0")
            let name = decodeUTF8Hex(raw["n"] as? String ?? "")
            let ip = raw["ip"] as? String ?? "--"
            let localIP = Self.localIPv4Address()
            let duration = Int(String(describing: raw["tf"] ?? "0")) ?? 0
            return ConnectedDevice(id: raw["i"] as? String ?? mac, name: name.isEmpty ? "دستگاه بی‌نام" : name, mac: mac, ip: ip, status: state, isOnline: state == "1" && !ip.isEmpty && ip != "NA", isBlocked: state == "2", isCurrentMac: ip == localIP, connectionType: String(describing: raw["ct"] ?? "Wi-Fi"), durationSeconds: duration, lastActive: String(describing: raw["ta"] ?? "--"), receivedBytes: safeCounter(raw["rx"]), sentBytes: safeCounter(raw["tx"]))
        }.sorted { ($0.isOnline ? 0 : $0.isBlocked ? 1 : 2) < ($1.isOnline ? 0 : $1.isBlocked ? 1 : 2) }
    }

    func manageDevice(_ device: ConnectedDevice, action: String) async throws {
        if device.isCurrentMac, action == "1" || action == "2" { throw ModemError.currentDeviceProtection }
        let result = try await post(file: "json_device_management_set", payload: ["action": action, "mac": device.mac])
        guard result["result"] as? String == "success" else { throw ModemError.modemRejected }
    }

    func reboot() async throws { _ = try await get(file: "json_device_restart") }

    func dhcpInfo() async throws -> DHCPInfo { DHCPInfo(json: try await get(file: "json_dhcp_info")) }

    func applyDNS(_ profile: DNSProfile, primary: String, secondary: String) async throws {
        let current = try await dhcpInfo()
        let useCustom = profile != .off
        let dns1 = profile == .custom ? primary.trimmingCharacters(in: .whitespaces) : profile.primary
        let dns2 = profile == .custom ? secondary.trimmingCharacters(in: .whitespaces) : profile.secondary
        if useCustom, !Self.isValidIPv4(dns1) { throw ModemError.invalidDNS("DNS اول معتبر نیست.") }
        if useCustom, !dns2.isEmpty, !Self.isValidIPv4(dns2) { throw ModemError.invalidDNS("DNS دوم معتبر نیست.") }
        let result = try await post(file: "json_lan_set", payload: [
            "status": "1", "dns_enable": useCustom ? "1" : "0", "dns1": dns1, "dns2": dns2,
            "start": current.start, "end": current.end, "lease_time": current.leaseTime, "ip": current.ip,
            "redirect_enable": "0", "redirect_url": ""
        ])
        guard result["result"] as? String == "success" else { throw ModemError.modemRejected }
        let verified = try await dhcpInfo()
        guard verified.dnsEnabled == useCustom,
              !useCustom || verified.dns1 == dns1
        else { throw ModemError.invalidDNS("مودم تنظیمات DNS را تأیید نکرد.") }
    }

    func resetTraffic() async throws {
        let result = try await post(file: "json_device_management_set", payload: ["action": "4"])
        guard result["result"] as? String == "success" else { throw ModemError.modemRejected }
    }

    nonisolated static func isValidIPv4(_ value: String) -> Bool {
        let parts = value.split(separator: ".", omittingEmptySubsequences: false)
        guard parts.count == 4 else { return false }
        return parts.allSatisfy { part in
            !part.isEmpty && part.allSatisfy(\.isNumber) && (part.count == 1 || part.first != "0") && UInt8(part) != nil
        }
    }


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

    static func localIPv4Address() -> String? {
        var pointer: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&pointer) == 0, let first = pointer else { return nil }
        defer { freeifaddrs(pointer) }
        var cursor: UnsafeMutablePointer<ifaddrs>? = first
        var fallback: String?
        while let current = cursor {
            defer { cursor = current.pointee.ifa_next }
            guard let address = current.pointee.ifa_addr, address.pointee.sa_family == UInt8(AF_INET) else { continue }
            let name = String(cString: current.pointee.ifa_name)
            guard name != "lo0" else { continue }
            var host = [CChar](repeating: 0, count: Int(NI_MAXHOST))
            var mutableAddress = address.pointee
            guard getnameinfo(&mutableAddress, socklen_t(address.pointee.sa_len), &host, socklen_t(host.count), nil, 0, NI_NUMERICHOST) == 0 else { continue }
            let bytes = host.prefix { $0 != 0 }.map { UInt8(bitPattern: $0) }
            let value = String(decoding: bytes, as: UTF8.self)
            if name == "en0" { return value }
            fallback = fallback ?? value
        }
        return fallback
    }

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
