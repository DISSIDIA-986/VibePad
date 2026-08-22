import ApplicationServices
import CoreGraphics
import Foundation

public enum InputSimulatorError: Error, CustomStringConvertible {
    case eventCreationFailed
    case accessibilityDenied

    public var description: String {
        switch self {
        case .eventCreationFailed:
            return "Failed to create CGEvent"
        case .accessibilityDenied:
            return "Accessibility permission required (System Settings → Privacy & Security → Accessibility)"
        }
    }
}

public struct InputSimulator: Sendable {
    public var eventSource: CGEventSource?
    /// Best method from `vibepad probe rctrl`; defaults to flags-changed (IME-friendly).
    public var rctrlMethod: RCtrlMethod

    public init(sourceStateID: CGEventSourceStateID = .hidSystemState, rctrlMethod: RCtrlMethod = .flagsChanged) {
        self.eventSource = CGEventSource(stateID: sourceStateID)
        self.rctrlMethod = rctrlMethod
    }

    /// Posts a single tap (keydown + keyup) for the combo.
    public func tap(_ combo: KeyCombo, interKeyDelayMs: Int = 2) throws {
        if combo.key == .rightControl && combo.modifiers.isEmpty {
            try RightControlProbe().fire(rctrlMethod, interMs: interKeyDelayMs)
            return
        }

        if combo.modifiers.contains(.maskCommand) {
            try tapModifiedCombo(key: combo.key, modifier: .maskCommand, interKeyDelayMs: interKeyDelayMs)
            return
        }

        if combo.modifiers.contains(.maskControl) {
            try tapModifiedCombo(key: combo.key, modifier: .maskControl, interKeyDelayMs: interKeyDelayMs)
            return
        }

        try postKey(combo.key, keyDown: true, flags: combo.modifiers)
        usleep(UInt32(interKeyDelayMs * 1000))
        try postKey(combo.key, keyDown: false, flags: combo.modifiers)
    }

    /// Modifier combos for Ghostty / IME: keep modifier flag on keyUp; bare keyUp leaks letters.
    private func tapModifiedCombo(key: KeyCode, modifier: CGEventFlags, interKeyDelayMs: Int) throws {
        let source = CGEventSource(stateID: .combinedSessionState)
        let tap: CGEventTapLocation = .cgAnnotatedSessionEventTap
        try postKey(key, keyDown: true, flags: modifier, source: source, tap: tap)
        usleep(UInt32(interKeyDelayMs * 1000))
        try postKey(key, keyDown: false, flags: modifier, source: source, tap: tap)
    }

    public func tap(spec: String) throws {
        try tap(try parseKeySpec(spec))
    }

    public func moveMouse(deltaX: Int, deltaY: Int) throws {
        guard let current = CGEvent(source: nil) else {
            throw InputSimulatorError.eventCreationFailed
        }
        let loc = current.location
        guard let move = CGEvent(
            mouseEventSource: eventSource,
            mouseType: .mouseMoved,
            mouseCursorPosition: CGPoint(x: loc.x + CGFloat(deltaX), y: loc.y + CGFloat(deltaY)),
            mouseButton: .left
        ) else {
            throw InputSimulatorError.eventCreationFailed
        }
        move.flags = []
        move.post(tap: .cghidEventTap)
    }

    private func postKey(
        _ key: KeyCode,
        keyDown: Bool,
        flags: CGEventFlags = [],
        source: CGEventSource? = nil,
        tap: CGEventTapLocation = .cghidEventTap
    ) throws {
        let eventSource = source ?? eventSource
        guard let event = CGEvent(
            keyboardEventSource: eventSource,
            virtualKey: key.rawValue,
            keyDown: keyDown
        ) else {
            throw InputSimulatorError.eventCreationFailed
        }
        event.flags = flags
        event.post(tap: tap)
    }

    private func postModifiers(_ modifiers: CGEventFlags, keyDown: Bool) throws {
        let keys: [KeyCode] = modifierKeys(for: modifiers)
        for key in keys {
            try postKey(key, keyDown: keyDown)
        }
    }

    private func modifierKeys(for flags: CGEventFlags) -> [KeyCode] {
        var keys: [KeyCode] = []
        if flags.contains(.maskCommand) { keys.append(.leftCommand) }
        if flags.contains(.maskControl) { keys.append(.leftControl) }
        return keys
    }
}

/// Returns true when the app can post events (best-effort; macOS may still block IME consumers).
public func checkAccessibilityTrusted(prompt: Bool = false) -> Bool {
    let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: prompt] as CFDictionary
    return AXIsProcessTrustedWithOptions(options)
}
