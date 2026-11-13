import Foundation
import Testing
@testable import MyModemApp

struct ColorContrastTests {
    @Test func bodyTextPairsMeetWCAGAA() {
        #expect(contrast("0F253D", "EAF3FA") >= 4.5)
        #expect(contrast("0F253D", "F8FBFD") >= 4.5)
        #expect(contrast("587088", "F8FBFD") >= 4.5)
        #expect(contrast("FFFFFF", "0A2342") >= 4.5)
        #expect(contrast("FFFFFF", "1464A5") >= 4.5)
    }

    private func contrast(_ foreground: String, _ background: String) -> Double {
        let first = luminance(foreground)
        let second = luminance(background)
        return (max(first, second) + 0.05) / (min(first, second) + 0.05)
    }

    private func luminance(_ hex: String) -> Double {
        let value = UInt64(hex, radix: 16) ?? 0
        let red = Double((value >> 16) & 255)
        let green = Double((value >> 8) & 255)
        let blue = Double(value & 255)
        let channels = [red, green, blue].map { component -> Double in
            let normalized: Double = component / 255.0
            if normalized <= 0.04045 { return normalized / 12.92 }
            return Foundation.pow((normalized + 0.055) / 1.055, 2.4)
        }
        return 0.2126 * channels[0] + 0.7152 * channels[1] + 0.0722 * channels[2]
    }
}
