import Foundation
import VibePadCore

enum CLI {
    static func run() {
        var args = Array(CommandLine.arguments.dropFirst())
        guard let cmd = args.first else {
            printUsage()
            exit(1)
        }
        args.removeFirst()

        switch cmd {
        case "test":
            runTest(args: args)
        case "run":
            runDaemon(args: args)
        case "doctor":
            runDoctor()
        case "bench":
            runBench(args: args)
        case "probe":
            runProbe(args: args)
        case "inject-rctrl":
            runInjectRctrl(args: args)
        case "help", "-h", "--help":
            printUsage()
        default:
            fputs("Unknown command: \(cmd)\n", stderr)
            printUsage()
            exit(1)
        }
    }

    private static func configURL(from args: [String]) -> URL {
        if let idx = args.firstIndex(of: "--config"), args.indices.contains(idx + 1) {
            return URL(fileURLWithPath: args[idx + 1])
        }
        let bundled = URL(fileURLWithPath: "config/default.yaml")
        if FileManager.default.fileExists(atPath: bundled.path) {
            return bundled
        }
        return ConfigPaths.defaultConfigURL
    }

    private static func runTest(args: [String]) {
        let key = args.first ?? "rctrl"
        guard checkAccessibilityTrusted(prompt: true) else {
            fputs("Accessibility permission required.\n", stderr)
            exit(1)
        }
        let sim = InputSimulator()
        do {
            try sim.tap(spec: key)
            print("Posted tap: \(key)")
        } catch {
            fputs("Error: \(error)\n", stderr)
            exit(1)
        }
    }

    private static func runDaemon(args: [String]) {
        let verbose = args.contains("--verbose") || args.contains("-v")
        let url = configURL(from: args)
        guard FileManager.default.fileExists(atPath: url.path) else {
            fputs("Config not found: \(url.path)\n", stderr)
            exit(1)
        }
        do {
            let config = try VibePadConfig.load(from: url)
            let daemon = VibePadDaemon(config: config, verbose: verbose)
            daemon.verbose = verbose
            daemon.run()
        } catch {
            fputs("Error: \(error)\n", stderr)
            exit(1)
        }
    }

    private static func runDoctor() {
        let trusted = checkAccessibilityTrusted(prompt: false)
        print("accessibility: \(trusted ? "ok" : "denied")")
        let gp = GamepadService()
        print("controller: \(gp.isConnected() ? gp.controllerName : "none")")
        print("frontmost: \(AppMonitor.frontmostBundleID() ?? "unknown")")
        let cfg = ConfigPaths.defaultConfigURL
        print("config: \(FileManager.default.fileExists(atPath: cfg.path) ? cfg.path : "missing (use config/default.yaml)")")

        let label = "dev.vibepad.spike-lb"
        let uid = getuid()
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/bin/launchctl")
        task.arguments = ["print", "gui/\(uid)/\(label)"]
        let pipe = Pipe()
        task.standardOutput = pipe
        task.standardError = Pipe()
        do {
            try task.run()
            task.waitUntilExit()
            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let out = String(data: data, encoding: .utf8) ?? ""
            if task.terminationStatus == 0 {
                let state = out.split(separator: "\n").first { $0.contains("state =") }
                let pid = out.split(separator: "\n").first { $0.contains("\tpid =") }
                print("launchd: \(state.map(String.init)?.trimmingCharacters(in: .whitespaces) ?? "loaded")")
                if let pid { print("  \(pid.trimmingCharacters(in: .whitespaces))") }
            } else {
                print("launchd: not loaded (run bin/install-daemon.sh)")
            }
        } catch {
            print("launchd: unknown")
        }

        let spikeRunning = Process()
        spikeRunning.executableURL = URL(fileURLWithPath: "/usr/bin/pgrep")
        spikeRunning.arguments = ["-f", "spike-lb-toggle.py"]
        spikeRunning.standardOutput = Pipe()
        spikeRunning.standardError = Pipe()
        try? spikeRunning.run()
        spikeRunning.waitUntilExit()
        print("spike: \(spikeRunning.terminationStatus == 0 ? "running" : "stopped")")
    }

    private static func runProbe(args: [String]) {
        let delaySec = args.compactMap { Int($0) }.first.map(Double.init) ?? 4
        guard checkAccessibilityTrusted(prompt: true) else {
            fputs("Accessibility permission required.\n", stderr)
            exit(1)
        }
        let probe = RightControlProbe()
        print("Probe: Ghostty focused + Doubao Toggle ready. Watch for voice start/stop.")
        print("Each method fires once, \(Int(delaySec))s apart.\n")
        for method in RCtrlMethod.allCases {
            print(">>> \(method.label)")
            fflush(stdout)
            Thread.sleep(forTimeInterval: 1)
            do {
                try probe.fire(method)
            } catch {
                print("    ERROR: \(error)")
            }
            Thread.sleep(forTimeInterval: delaySec)
        }
        print("\nDone. Reply with the number that toggled Doubao (e.g. 3).")
    }

    private static func runInjectRctrl(args: [String]) {
        let force = args.contains("--force") || args.contains("-f")
        let debounceMs = args.compactMap { arg -> Int? in
            guard arg.hasPrefix("--debounce=") else { return nil }
            return Int(arg.dropFirst("--debounce=".count))
        }.first ?? RCtrlInjector.defaultDebounceMs

        guard checkAccessibilityTrusted(prompt: true) else {
            fputs("Accessibility permission required.\n", stderr)
            exit(1)
        }

        let injector = RCtrlInjector(debounceMs: debounceMs)
        do {
            try injector.inject(force: force)
            exit(0)
        } catch RCtrlInjectorError.debounced {
            exit(0)
        } catch {
            fputs("Error: \(error)\n", stderr)
            exit(1)
        }
    }

    private static func runBench(args: [String]) {
        let n = Int(args.first ?? "1000") ?? 1000
        guard checkAccessibilityTrusted(prompt: false) else {
            fputs("Accessibility permission required.\n", stderr)
            exit(1)
        }
        let sim = InputSimulator()
        var samples: [Double] = []
        samples.reserveCapacity(n)
        for _ in 0..<n {
            let start = CFAbsoluteTimeGetCurrent()
            try? sim.tap(spec: "rctrl")
            samples.append((CFAbsoluteTimeGetCurrent() - start) * 1000)
        }
        samples.sort()
        let p50 = samples[samples.count / 2]
        let p99 = samples[Int(Double(samples.count) * 0.99)]
        print(String(format: "p50=%.2fms p99=%.2fms (n=%d)", p50, p99, n))
    }

    private static func printUsage() {
        print("""
        vibepad — Xbox gamepad → keyboard/mouse for Ghostty + Doubao IME

        Usage:
          vibepad test [rctrl|enter|cmd+z|...]   Gate 0: post one key tap
          vibepad inject-rctrl [--force]         Spike bridge: debounced flagsChanged rctrl
          vibepad probe rctrl [delaySec]         Try all rctrl injection methods
          vibepad run [--config path]              Foreground daemon
          vibepad doctor                           Permission / controller check
          vibepad bench [n]                        Latency benchmark

        Spike checklist: docs/spike/GATE0.md
        """)
    }
}

CLI.run()
