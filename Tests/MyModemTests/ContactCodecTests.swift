import Foundation
import Testing
@testable import MyModemApp

struct ContactCodecTests {
    private func contact(_ name: String, _ number: String) -> ModemContact {
        let record = ContactRecord(id: name, name: name, number: number, normalizedNumber: number, group: .family, storage: .sim)
        return ModemContact(normalizedNumber: number, preferredName: name, records: [record])
    }

    @Test func exportsValidVCard() {
        let text = ContactCodec.vCard([contact("علی رضایی", "09120000000")])
        #expect(text.contains("BEGIN:VCARD"))
        #expect(text.contains("FN:علی رضایی"))
        #expect(text.contains("TEL;TYPE=CELL:09120000000"))
        #expect(text.hasSuffix("END:VCARD\r\n"))
    }

    @Test func exportsQuotedCSVWithHeader() {
        let text = ContactCodec.csv([contact("علی, رضایی", "09120000000")])
        let lines = text.components(separatedBy: "\n")
        #expect(lines.first == "name,number,group,storage")
        #expect(text.contains("\"علی, رضایی\""))
    }

    @Test func parsesVCardWithCategories() {
        let text = """
        BEGIN:VCARD
        VERSION:3.0
        FN:سارا
        TEL;TYPE=CELL:09121111111
        CATEGORIES:دوستان
        END:VCARD
        """
        let parsed = ContactCodec.parse(text)
        #expect(parsed.count == 1)
        #expect(parsed.first?.name == "سارا")
        #expect(parsed.first?.group == .friend)
    }

    @Test func parsesCSVAndSkipsHeaderAndInvalidRows() {
        let text = """
        name,number,group,storage
        علی,09120000000,خانواده,سیم‌کارت
        بدون شماره,,,
        رضا,+989123333333,همکاران,مودم
        """
        let parsed = ContactCodec.parse(text)
        #expect(parsed.count == 2)
        #expect(parsed.map(\.name) == ["علی", "رضا"])
        #expect(parsed.last?.group == .colleague)
    }

    @Test func roundTripsThroughCSV() {
        let original = [contact("مریم", "09125555555")]
        let parsed = ContactCodec.parse(ContactCodec.csv(original))
        #expect(parsed.first?.number == "09125555555")
        #expect(parsed.first?.name == "مریم")
    }
}
