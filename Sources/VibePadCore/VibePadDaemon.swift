import Foundation

public final class VibePadDaemon: @unchecked Sendable {
    private let config: VibePadConfig
    private let simulator = InputSimulator()
    private let gamepad: GamepadService
    private var debouncer = EdgeDebouncer(intervalMs: 50)
    private var pollTimer: DispatchSourceTimer?
    private let queue = DispatchQueue(label: "dev.vibepad.daemon", qos: .userInteractive)
    public var verbose: Bool = false

    public init(config: VibePadConfig, verbose: Bool = false) {
        self.config = config
        self.verbose = verbose
        self.gamepad = GamepadService(verbose: verbose)
    }

    /// Start polling without blocking the caller's run loop (for VibePad.app).
    @discardableResult
    public func start() -> Bool {
        guard checkAccessibilityTrusted(prompt: true) else {
            fputs("Accessibility permission required.\n", stderr)
            return false
        }

        gamepad.onButtonEdge = { [weak self] button in
            self?.handleButton(button)
        }
        gamepad.onStick = { [weak self] stickID, sample in
            self?.handleStick(stickID: stickID, sample: sample)
        }

        let interval = 1.0 / config.pollHz
        let timer = DispatchSource.makeTimerSource(queue: queue)
        timer.schedule(deadline: .now(), repeating: interval)
        timer.setEventHandler { [weak self] in
            self?.gamepad.pollSticks()
        }
        timer.resume()
        pollTimer = timer

        fputs("VibePad running (poll \(Int(config.pollHz))Hz). Controller: \(gamepad.controllerName)\n", stderr)
        return true
    }

    public func run() {
        guard start() else { exit(1) }
        RunLoop.main.run()
    }

    private func handleButton(_ button: GamepadButton) {
        let bundleID = AppMonitor.frontmostBundleID()
        guard let bundleID,
              let profile = config.profile(matching: bundleID),
              let actions = profile.buttons,
              let action = actions[button.id] else {
            if verbose {
                fputs("[vibepad] ignored \(button.id) — frontmost=\(bundleID ?? "nil") (need Ghostty)\n", stderr)
            }
            return
        }

        let nowMs = Int64(Date().timeIntervalSince1970 * 1000)
        guard debouncer.shouldFire(buttonID: button.id, nowMs: nowMs) else { return }

        queue.async { [simulator, verbose] in
            do {
                let spec = try action.resolvedSpec()
                try simulator.tap(spec: spec)
                if verbose {
                    fputs("[vibepad] fired \(button.id) → \(spec)\n", stderr)
                }
            } catch {
                fputs("Button \(button.id) error: \(error)\n", stderr)
            }
        }
    }

    private func handleStick(stickID: String, sample: StickSample) {
        guard let bundleID = AppMonitor.frontmostBundleID(),
              let profile = config.profile(matching: bundleID),
              let sticks = profile.sticks,
              let stick = sticks[stickID],
              stick.mode == "mouse_move" else {
            return
        }

        let cfg = stick.mouseMoveConfig(pollHz: config.pollHz)
        let delta = MouseEngine.delta(for: sample, config: cfg)
        guard delta.deltaX != 0 || delta.deltaY != 0 else { return }

        queue.async { [simulator] in
            do {
                try simulator.moveMouse(deltaX: Int(delta.deltaX.rounded()), deltaY: Int(delta.deltaY.rounded()))
            } catch {
                fputs("Stick error: \(error)\n", stderr)
            }
        }
    }
}
