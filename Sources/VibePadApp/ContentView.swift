import AppKit
import SwiftUI

struct ContentView: View {
    @EnvironmentObject private var model: AppModel

    var body: some View {
        Group {
            Text("VibePad")
                .font(.headline)
            Text(model.statusMessage)
                .font(.caption)
                .foregroundStyle(.secondary)
            Divider()
            Label(
                model.controllerName == "none" ? "No controller" : model.controllerName,
                systemImage: "gamecontroller"
            )
            Label(
                model.accessibilityGranted ? "Accessibility OK" : "Accessibility denied",
                systemImage: model.accessibilityGranted ? "checkmark.circle" : "xmark.circle"
            )
            Divider()
            if model.daemonRunning {
                Button("Stop GameController daemon") { model.stopDaemon() }
            } else {
                Button("Start GameController daemon (experimental)") { model.startDaemon() }
            }
            Button("Open spike log…") { model.openLog() }
            Divider()
            Button("Quit VibePad") { NSApplication.shared.terminate(nil) }
        }
        .onAppear { model.onAppear() }
        .onDisappear { model.onDisappear() }
    }
}
