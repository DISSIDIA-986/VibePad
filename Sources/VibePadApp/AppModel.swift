import AppKit
import Foundation
import VibePadCore

@MainActor
final class AppModel: ObservableObject {
    @Published var controllerName = "none"
    @Published var daemonRunning = false
    @Published var accessibilityGranted = false
    @Published var statusMessage = "Idle"

    private var daemon: VibePadDaemon?
    private var refreshTimer: Timer?

    func onAppear() {
        accessibilityGranted = checkAccessibilityTrusted(prompt: false)
        refreshTimer = Timer.scheduledTimer(withTimeInterval: 2.0, repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refreshStatus() }
        }
        refreshStatus()
    }

    func onDisappear() {
        refreshTimer?.invalidate()
        stopDaemon()
    }

    func refreshStatus() {
        accessibilityGranted = checkAccessibilityTrusted(prompt: false)
        let gp = GamepadService(verbose: false)
        controllerName = gp.isConnected() ? gp.controllerName : "none"
        let spike = Process()
        spike.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
        spike.arguments = ["-f", "spike-lb-toggle.py"]
        spike.standardOutput = Pipe()
        spike.standardError = Pipe()
        try? spike.run()
        spike.waitUntilExit()
        let spikeRunning = spike.terminationStatus == 0
        if daemonRunning && spikeRunning {
            statusMessage = "Both active: spike (Python) + GameController — stop one to avoid duplicate input"
        } else if daemonRunning {
            statusMessage = "GameController daemon active"
        } else if spikeRunning {
            statusMessage = "Spike daemon active (launchd)"
        } else {
            statusMessage = "No input daemon running"
        }
    }

    func startDaemon() {
        guard checkAccessibilityTrusted(prompt: true) else {
            accessibilityGranted = false
            statusMessage = "Accessibility permission required"
            return
        }
        accessibilityGranted = true
        let spike = Process()
        spike.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
        spike.arguments = ["-f", "spike-lb-toggle.py"]
        spike.standardOutput = Pipe()
        spike.standardError = Pipe()
        try? spike.run()
        spike.waitUntilExit()
        if spike.terminationStatus == 0 {
            statusMessage = "Spike still running — run bin/uninstall-daemon.sh first, or LB will keep using spike"
        }
        stopDaemon()
        do {
            let config = try VibePadConfig.load(from: ConfigPaths.defaultConfigURL)
            let d = VibePadDaemon(config: config, verbose: true)
            guard d.start() else {
                statusMessage = "Accessibility permission required"
                return
            }
            daemon = d
            daemonRunning = true
            refreshStatus()
        } catch {
            statusMessage = "Start failed: \(error.localizedDescription)"
        }
    }

    func stopDaemon() {
        daemon = nil
        daemonRunning = false
        refreshStatus()
    }

    func openLog() {
        NSWorkspace.shared.open(URL(fileURLWithPath: "/tmp/spike-lb-toggle.log"))
    }
}
