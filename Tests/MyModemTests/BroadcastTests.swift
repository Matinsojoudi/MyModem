import Foundation
import Testing
@testable import MyModemApp

@MainActor
struct BroadcastTests {
    private let csv = """
    شماره دانشجویی,نام,نام‌خانوادگی,موبایل,ایمیل
    14054421001,اسما,ابادی,9939541231,a@example.com
    14054421002,علی,اسدپور,9058813927,b@example.com
    14054421002,علی,اسدپور,9058813927,duplicate@example.com
    """

    @Test func parsesPersianHeaderAndNormalizesTenDigitNumbers() throws {
        let list = try RecipientParser.parse(data: Data(csv.utf8))
        #expect(list.phoneColumn == "موبایل")
        #expect(list.rows.count == 2)
        #expect(list.rows[0].phone == "09939541231")
        #expect(list.rows[0].raw["نام"] == "اسما")
        #expect(list.rows[0].raw["نام کامل"] == "اسما ابادی")
    }

    @Test func ignoresStudentIdColumnForPhoneDetection() throws {
        let list = try RecipientParser.parse(data: Data(csv.utf8))
        #expect(list.rows.allSatisfy { $0.phone.hasPrefix("09") })
    }

    @Test func rendersVariablesPerRecipient() throws {
        let list = try RecipientParser.parse(data: Data(csv.utf8))
        let template = "سلام {{نام کامل}}، کد شما {{شماره دانشجویی}} است."
        let text = TemplateRenderer.render(template, with: list.rows[1].raw)
        #expect(text == "سلام علی اسدپور، کد شما 14054421002 است.")
    }

    @Test func missingVariableBecomesEmpty() {
        let text = TemplateRenderer.render("سلام {{نام کامل}}", with: [:])
        #expect(text == "سلام ")
    }

    @Test func detectsVariablesAndUnknownKeys() throws {
        let list = try RecipientParser.parse(data: Data(csv.utf8))
        let engine = BroadcastEngine()
        engine.load(url: try write(csv))
        engine.template = "{{نام کامل}} - {{موبایل}} - {{ناشناس}}"
        #expect(engine.missingVariables == ["ناشناس"])
        #expect(TemplateRenderer.variables(in: engine.template).count == 3)
        #expect(list.rows.count == 2)
    }

    @Test func parsesWindowsCRLFAndBOM() throws {
        let windows = "\u{FEFF}نام,موبایل\r\nعلی,9123456789\r\nسارا,09351234567\r\n"
        let list = try RecipientParser.parse(data: Data(windows.utf8))
        #expect(list.rows.count == 2)
        #expect(list.rows[0].phone == "09123456789")
        #expect(list.rows[1].phone == "09351234567")
    }

    @Test func handlesQuotedFieldsWithCommasAndNewlines() {
        let table = RecipientParser.parseTable("a,b\n\"x,y\",\"line1\nline2\"\n")
        #expect(table.count == 2)
        #expect(table[1][0] == "x,y")
        #expect(table[1][1] == "line1\nline2")
    }

    @Test func rejectsFileWithoutPhoneColumn() {
        #expect(throws: BroadcastError.self) {
            try RecipientParser.parse(data: Data("name,email\nali,a@b.c\n".utf8))
        }
    }

    @Test func reportCSVEscapesQuotes() {
        let engine = BroadcastEngine()
        engine.load(url: try! write(csv))
        let csvOut = engine.reportCSV()
        #expect(csvOut.hasPrefix("name,phone,status"))
        #expect(csvOut.contains("09939541231"))
    }

    private func write(_ content: String) throws -> URL {
        let url = FileManager.default.temporaryDirectory.appending(path: "broadcast-\(UUID().uuidString).csv")
        try Data(content.utf8).write(to: url)
        return url
    }
}
