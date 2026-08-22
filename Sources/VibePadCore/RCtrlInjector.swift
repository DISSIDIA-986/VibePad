import Foundation

public enum RCtrlInjectorError: Error, CustomStringConvertible {
    case debounced
    case accessibilityDenied

    public var description: String {
        switch self {
        case .debounced:
            return "Debounced (too soon after previous inject)"
        case .accessibilityDenied:
            return "Accessibility permission required"
        }
    }
}

/// Cross-process debounced Right Ctrl toggle for padjutsu shell bridge.
public struct RCtrlInjector: Sendable {
    public static let defaultDebounceMs = 200
    public static let stampPath = "/tmp/vibepad-inject-rctrl.ts"
    public static let logPath = "/tmp/vibepad-inject.log"

    public var debounceMs: Int
    public var method: RCtrlMethod

    public init(debounceMs: Int = Self.defaultDebounceMs, method: RCtrlMethod = .flagsChanged) {
        self.debounceMs = debounceMs
        self.method = method
    }

    /// Posts one Right Ctrl tap. Returns `.debounced` when called too soon after the last inject.
    public func inject(force: Bool = false) throws {
        guard checkAccessibilityTrusted(prompt: false) else {
            throw RCtrlInjectorError.accessibilityDenied
        }
        if !force, isDebounced() {
            appendLog("skip debounced")
            throw RCtrlInjectorError.debounced
        }
        stampNow()
        try RightControlProbe().fire(method)
        appendLog("ok method=\(method.rawValue)")
    }

    private func isDebounced() -> Bool {
        guard let text = try? String(contentsOfFile: Self.stampPath, encoding: .utf8),
              let lastMs = Double(text.trimmingCharacters(in: .whitespacesAndNewlines))
        else {
            return false
        }
        let nowMs = Date().timeIntervalSince1970 * 1000
        return nowMs - lastMs < Double(debounceMs)
    }

    private func stampNow() {
        let nowMs = Date().timeIntervalSince1970 * 1000
        try? String(format: "%.0f", nowMs).write(toFile: Self.stampPath, atomically: true, encoding: .utf8)
    }

    private func appendLog(_ message: String) {
        let ts = ISO8601DateFormatter().string(from: Date())
        let line = "[\(ts)] \(message)\n"
        if FileManager.default.fileExists(atPath: Self.logPath),
           let handle = FileHandle(forWritingAtPath: Self.logPath)
        {
            handle.seekToEndOfFile()
            handle.write(line.data(using: .utf8)!)
            try? handle.close()
        } else {
            FileManager.default.createFile(atPath: Self.logPath, contents: line.data(using: .utf8))
        }
    }
}
