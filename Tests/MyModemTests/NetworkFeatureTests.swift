import Foundation
import Testing
@testable import MyModemApp

struct NetworkFeatureTests {
    @Test(arguments: ["1.1.1.3", "94.140.14.15", "192.168.1.1", "8.8.8.8"])
    func acceptsWellFormedDNSAddresses(_ value: String) {
        #expect(ModemClient.isValidIPv4(value))
    }

    @Test(arguments: ["", "1.1.1", "1.1.1.256", "1.1.1.3.4", "dns.example.com", "01.1.1.1", "1.1.1.-1"])
    func rejectsMalformedDNSAddresses(_ value: String) {
        #expect(!ModemClient.isValidIPv4(value))
    }

    @Test func parsesDHCPResponseFields() {
        let info = DHCPInfo(json: [
            "dns_enable": "1", "dns1": "1.1.1.3", "dns2": "1.0.0.3",
            "start": "192.168.1.100", "end": "192.168.1.200",
            "lease_time": "86400", "ip": "192.168.1.1"
        ])
        #expect(info.dnsEnabled)
        #expect(info.dns1 == "1.1.1.3")
        #expect(info.dns2 == "1.0.0.3")
        #expect(info.leaseTime == "86400")
        #expect(info.ip == "192.168.1.1")
    }

    @Test func disabledDNSDoesNotClaimCustomServers() {
        let info = DHCPInfo(json: ["dns_enable": "0", "dns1": "", "dns2": ""])
        #expect(!info.dnsEnabled)
        #expect(info.dns1.isEmpty)
    }

    @Test func dnsProfilesExposeExpectedPresets() {
        #expect(DNSProfile.cloudflareFamily.primary == "1.1.1.3")
        #expect(DNSProfile.adguardFamily.secondary == "94.140.15.16")
        #expect(DNSProfile.off.primary.isEmpty)
    }

    @Test func selfDeviceCannotBeDisconnectedOrBlocked() async {
        let device = ConnectedDevice(id: "1", name: "mac", mac: "aa:bb:cc:dd:ee:ff", ip: "192.168.1.120", status: "1", isOnline: true, isBlocked: false, isCurrentMac: true, connectionType: "Wi-Fi", durationSeconds: 60, lastActive: "now", receivedBytes: 0, sentBytes: 0)
        let client = ModemClient(host: "192.168.1.1")
        await #expect(throws: ModemError.self) { try await client.manageDevice(device, action: "2") }
        await #expect(throws: ModemError.self) { try await client.manageDevice(device, action: "1") }
    }
}
