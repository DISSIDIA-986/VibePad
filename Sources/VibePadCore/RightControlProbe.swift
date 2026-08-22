import CoreGraphics
import Foundation

public enum RCtrlMethod: String, CaseIterable, Sendable {
    case keyDownUp = "key-down-up"
    case keyDownUpWithMask = "key-down-up-mask"
    case flagsChanged = "flags-changed"
    case flagsChangedAnnotated = "flags-changed-annotated"
    case combinedSessionSource = "combined-session"
    case leftControlKeyDownUp = "left-ctrl-fallback"

    public var label: String {
        switch self {
        case .keyDownUp: return "1 keyDown/keyUp 0x3E (original)"
        case .keyDownUpWithMask: return "2 keyDown/keyUp 0x3E + maskControl flag"
        case .flagsChanged: return "3 flagsChanged 0x3E HID tap"
        case .flagsChangedAnnotated: return "4 flagsChanged 0x3E annotated tap"
        case .combinedSessionSource: return "5 flagsChanged + combinedSession source"
        case .leftControlKeyDownUp: return "6 left Control 0x3B (sanity check)"
        }
    }
}

public struct RightControlProbe: Sendable {
    public init() {}

    public func fire(_ method: RCtrlMethod, interMs: Int = 8) throws {
        switch method {
        case .keyDownUp:
            try postKey(.rightControl, keyDown: true, flags: [], tap: .cghidEventTap, source: .hidSystemState)
            usleep(UInt32(interMs * 1000))
            try postKey(.rightControl, keyDown: false, flags: [], tap: .cghidEventTap, source: .hidSystemState)
        case .keyDownUpWithMask:
            try postKey(.rightControl, keyDown: true, flags: .maskControl, tap: .cghidEventTap, source: .hidSystemState)
            usleep(UInt32(interMs * 1000))
            try postKey(.rightControl, keyDown: false, flags: .maskControl, tap: .cghidEventTap, source: .hidSystemState)
        case .flagsChanged:
            try postFlagsChanged(.rightControl, pressed: true, tap: .cghidEventTap, source: .hidSystemState)
            usleep(UInt32(interMs * 1000))
            try postFlagsChanged(.rightControl, pressed: false, tap: .cghidEventTap, source: .hidSystemState)
        case .flagsChangedAnnotated:
            try postFlagsChanged(.rightControl, pressed: true, tap: .cgAnnotatedSessionEventTap, source: .hidSystemState)
            usleep(UInt32(interMs * 1000))
            try postFlagsChanged(.rightControl, pressed: false, tap: .cgAnnotatedSessionEventTap, source: .hidSystemState)
        case .combinedSessionSource:
            try postFlagsChanged(.rightControl, pressed: true, tap: .cghidEventTap, source: .combinedSessionState)
            usleep(UInt32(interMs * 1000))
            try postFlagsChanged(.rightControl, pressed: false, tap: .cghidEventTap, source: .combinedSessionState)
        case .leftControlKeyDownUp:
            try postKey(.leftControl, keyDown: true, flags: [], tap: .cghidEventTap, source: .hidSystemState)
            usleep(UInt32(interMs * 1000))
            try postKey(.leftControl, keyDown: false, flags: [], tap: .cghidEventTap, source: .hidSystemState)
        }
    }

    private func postKey(
        _ key: KeyCode,
        keyDown: Bool,
        flags: CGEventFlags,
        tap: CGEventTapLocation,
        source: CGEventSourceStateID
    ) throws {
        let eventSource = CGEventSource(stateID: source)
        guard let event = CGEvent(keyboardEventSource: eventSource, virtualKey: key.rawValue, keyDown: keyDown) else {
            throw InputSimulatorError.eventCreationFailed
        }
        event.flags = flags
        event.post(tap: tap)
    }

    private func postFlagsChanged(
        _ key: KeyCode,
        pressed: Bool,
        tap: CGEventTapLocation,
        source: CGEventSourceStateID
    ) throws {
        let eventSource = CGEventSource(stateID: source)
        guard let event = CGEvent(keyboardEventSource: eventSource, virtualKey: key.rawValue, keyDown: pressed) else {
            throw InputSimulatorError.eventCreationFailed
        }
        event.type = .flagsChanged
        event.flags = pressed ? .maskControl : []
        event.post(tap: tap)
    }
}
