import SwiftUI

@main
struct VibePadAppMain: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        MenuBarExtra("VibePad", systemImage: "gamecontroller.fill") {
            ContentView()
                .environmentObject(model)
        }
        .menuBarExtraStyle(.menu)
    }
}
