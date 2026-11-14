import Testing
@testable import MyModemApp

struct ModemHostValidatorTests {
    @Test(arguments: ["192.168.1.1", "10.0.0.1", "172.16.0.1", "172.31.255.254"])
    func acceptsPrivateIPv4(_ value: String) throws {
        #expect(try ModemHost(value).value == value)
    }

    @Test(arguments: [
        "127.0.0.1", "169.254.1.1", "0.0.0.0", "8.8.8.8",
        "192.168.1.1:8080", "http://192.168.1.1", "192.168.1.1/path",
        "metadata.google.internal", "localhost", ""
    ])
    func rejectsUnsafeOrMalformedHosts(_ value: String) {
        #expect(throws: ModemHost.ValidationError.self) { try ModemHost(value) }
    }

    @Test func canonicalizesWhitespace() throws {
        #expect(try ModemHost(" 192.168.1.1 ").value == "192.168.1.1")
    }
}
