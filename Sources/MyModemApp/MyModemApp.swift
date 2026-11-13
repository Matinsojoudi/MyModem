import SwiftUI

@main
struct MyModemApplication: App {
    @State private var state = AppState()

    var body: some Scene {
        WindowGroup("MyModem") {
            RootView(state: state)
                .task { state.start() }
                .onDisappear { state.stop() }
        }
        .defaultSize(width: 1100, height: 720)
        .commands {
            CommandGroup(after: .toolbar) {
                Button("تازه‌سازی وضعیت") { Task { await state.refresh() } }
                    .keyboardShortcut("r", modifiers: .command)
            }
        }

        MenuBarExtra {
            Button("باز کردن MyModem") { NSApplication.shared.activate(ignoringOtherApps: true) }
            Divider()
            Text(state.isOnline ? "مودم متصل است" : "مودم آفلاین است")
            if let status = state.status {
                Text("باتری: \(status.batteryPercent)%")
                Text("سیگنال: \(status.signalQuality)/5")
                Text("پیام جدید: \(status.unreadMessages)")
            }
            Divider()
            Button("تازه‌سازی") { Task { await state.refresh() } }
            Button("خروج") { NSApplication.shared.terminate(nil) }
        } label: {
            Label(menuTitle, systemImage: menuSymbol)
        }
        .menuBarExtraStyle(.menu)
    }

    private var menuTitle: String {
        guard let status = state.status else { return "مودم" }
        return "\(status.batteryPercent)%"
    }

    private var menuSymbol: String {
        guard let status = state.status else { return "wifi.slash" }
        if status.isCharging { return "bolt.fill" }
        if status.batteryPercent <= 10 { return "battery.0percent" }
        return "battery.75percent"
    }
}
