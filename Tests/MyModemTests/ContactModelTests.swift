import Testing
@testable import MyModemApp

struct ContactModelTests {
    @Test func initialsUseFirstTwoWords() {
        let record = ContactRecord(id: "1", name: "متین سجودی", number: "09123456789", normalizedNumber: "09123456789", group: .friend, storage: .sim)
        let contact = ModemContact(normalizedNumber: record.normalizedNumber, preferredName: record.name, records: [record])
        #expect(contact.initials == "مس")
        #expect(contact.hasSIMRecord)
        #expect(!contact.hasModemRecord)
    }

    @Test func unifiedContactPreservesSIMAndModemRecords() {
        let sim = ContactRecord(id: "s1", name: "علی", number: "09120000000", normalizedNumber: "09120000000", group: .family, storage: .sim)
        let modem = ContactRecord(id: "m1", name: "علی محمدی", number: "+989120000000", normalizedNumber: "09120000000", group: .family, storage: .modem)
        let contact = ModemContact(normalizedNumber: sim.normalizedNumber, preferredName: modem.name, records: [sim, modem])
        #expect(contact.allIDs == ["s1", "m1"])
        #expect(contact.hasSIMRecord)
        #expect(contact.hasModemRecord)
        #expect(contact.storage == "سیم‌کارت و مودم")
    }

    @Test func unnamedContactHasFallbackInitial() {
        let record = ContactRecord(id: "2", name: "", number: "", normalizedNumber: "", group: .common, storage: .modem)
        let contact = ModemContact(normalizedNumber: "", preferredName: "", records: [record])
        #expect(contact.initials == "؟")
    }
}
