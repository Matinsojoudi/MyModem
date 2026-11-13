import SwiftUI

/* Hallmark · native-dashboard · tone: soft-friendly · anchor hue: navy */
enum ModemTheme {
    static let navy = Color(red: 10/255, green: 35/255, blue: 66/255)
    static let navyRaised = Color(red: 18/255, green: 52/255, blue: 88/255)
    static let blue = Color(red: 20/255, green: 100/255, blue: 165/255)
    static let sky = Color(red: 83/255, green: 165/255, blue: 220/255)
    static let canvas = Color(red: 234/255, green: 243/255, blue: 250/255)
    static let surface = Color(red: 248/255, green: 251/255, blue: 253/255)
    static let line = Color(red: 205/255, green: 222/255, blue: 235/255)
    static let ink = Color(red: 15/255, green: 37/255, blue: 61/255)
    static let muted = Color(red: 88/255, green: 112/255, blue: 136/255)
    static let success = Color(red: 32/255, green: 151/255, blue: 109/255)
    static let warning = Color(red: 224/255, green: 145/255, blue: 48/255)
    static let danger = Color(red: 202/255, green: 71/255, blue: 71/255)
}

struct NavyButtonStyle: ButtonStyle {
    @Environment(\.isEnabled) private var enabled
    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 13, weight: .semibold, design: .rounded))
            .foregroundStyle(.white)
            .padding(.horizontal, 18).padding(.vertical, 10)
            .background(enabled ? ModemTheme.blue : ModemTheme.muted.opacity(0.45), in: Capsule())
            .scaleEffect(configuration.isPressed ? 0.97 : 1)
            .opacity(configuration.isPressed ? 0.86 : 1)
            .animation(.easeOut(duration: 0.1), value: configuration.isPressed)
    }
}

struct SoftCard<Content: View>: View {
    @ViewBuilder let content: Content
    var body: some View {
        content.padding(20)
            .foregroundStyle(ModemTheme.ink)
            .background(ModemTheme.surface, in: RoundedRectangle(cornerRadius: 20, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 20, style: .continuous).stroke(ModemTheme.line.opacity(0.8)))
            .shadow(color: ModemTheme.navy.opacity(0.055), radius: 18, y: 8)
    }
}

struct BrandMark: View {
    var size: CGFloat = 42
    var body: some View {
        ZStack {
            RoundedRectangle(cornerRadius: size * 0.26, style: .continuous)
                .fill(LinearGradient(colors: [ModemTheme.sky, ModemTheme.blue], startPoint: .topLeading, endPoint: .bottomTrailing))
            Image(systemName: "wifi.router.fill")
                .font(.system(size: size * 0.52, weight: .semibold))
                .foregroundStyle(.white)
        }.frame(width: size, height: size)
    }
}

struct ModemTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .foregroundStyle(ModemTheme.ink)
            .tint(ModemTheme.blue)
            .padding(.horizontal, 12)
            .frame(minHeight: 38)
            .background(Color.white, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(ModemTheme.line, lineWidth: 1))
    }
}

extension View {
    func appCanvas() -> some View {
        background(ModemTheme.canvas).foregroundStyle(ModemTheme.ink)
    }

    func modemInputSurface() -> some View {
        foregroundStyle(ModemTheme.ink)
            .tint(ModemTheme.blue)
            .background(Color.white, in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            .overlay(RoundedRectangle(cornerRadius: 10, style: .continuous).stroke(ModemTheme.line, lineWidth: 1))
    }
}
