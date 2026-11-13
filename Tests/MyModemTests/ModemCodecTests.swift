import Testing
@testable import MyModemApp

struct ModemCodecTests {
    let codec = ModemCodec()

    @Test func roundTripPersianAndEmoji() {
        let value = "سلام مودم 📶\nخط دوم"
        #expect(codec.decode(codec.encode(value)) == value)
    }

    @Test func recursiveDecode() {
        let once = codec.encode("سلام")
        let twice = codec.encode(once)
        #expect(codec.decode(twice) == "سلام")
    }

    @Test func normalizesArabicGlyphs() {
        #expect(codec.decode("0643064A0649") == "کیی")
    }

    @Test func normalizesIranianPhoneNumbers() {
        #expect(codec.normalizePhone("+98 912-345-6789") == "09123456789")
        #expect(codec.normalizePhone("۹۱۲۳۴۵۶۷۸۹") == "09123456789")
        #expect(codec.normalizePhone("00989123456789") == "09123456789")
    }

    @Test func formatsJalaliTimestamp() {
        let formatter = JalaliDateFormatter()
        #expect(formatter.string(fromModemTimestamp: "26,10,03,19,06,11,+3") == "11 مهر 1405 - ساعت 19:06")
    }
}
