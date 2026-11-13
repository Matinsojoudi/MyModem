import Testing
@testable import MyModemApp

struct ContactModelTests {
    @Test func initialsUseFirstTwoWords() {
        let contact = ModemContact(id: "1", allIDs: ["1"], name: "متین سجودی", number: "09123456789", normalizedNumber: "09123456789", group: "دوستان", storage: "سیم‌کارت")
        #expect(contact.initials == "مس")
    }

    @Test func unnamedContactHasFallbackInitial() {
        let contact = ModemContact(id: "2", allIDs: ["2"], name: "", number: "", normalizedNumber: "", group: "عمومی", storage: "دستگاه")
        #expect(contact.initials == "؟")
    }
}
