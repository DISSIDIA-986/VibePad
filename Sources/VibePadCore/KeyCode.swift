import CoreGraphics

public enum KeyCode: CGKeyCode, Sendable {
    case enter = 0x24
    case backspace = 0x33
    case leftControl = 0x3B
    case rightControl = 0x3E
    case leftCommand = 0x37
    case z = 0x06
    case u = 0x20
    case grave = 0x32
}

public struct KeyCombo: Sendable {
    public let key: KeyCode
    public let modifiers: CGEventFlags

    public init(key: KeyCode, modifiers: CGEventFlags = []) {
        self.key = key
        self.modifiers = modifiers
    }

    public static let enter = KeyCombo(key: .enter)
    public static let backspace = KeyCombo(key: .backspace)
    public static let rightControl = KeyCombo(key: .rightControl)
    public static let cmdEnter = KeyCombo(key: .enter, modifiers: .maskCommand)
    public static let cmdZ = KeyCombo(key: .z, modifiers: .maskCommand)
    public static let ctrlU = KeyCombo(key: .u, modifiers: .maskControl)
}

public enum KeyParseError: Error, CustomStringConvertible {
    case unknownToken(String)

    public var description: String {
        switch self {
        case .unknownToken(let token):
            return "Unknown key token: \(token)"
        }
    }
}

/// Parses `rctrl`, `enter`, `backspace`, or combos like `cmd+enter`, `cmd+z`.
public func parseKeySpec(_ spec: String) throws -> KeyCombo {
    let parts = spec.lowercased().split(separator: "+").map(String.init)
    guard let last = parts.last else {
        throw KeyParseError.unknownToken(spec)
    }

    var modifiers: CGEventFlags = []
    for part in parts.dropLast() {
        switch part {
        case "cmd", "command", "lcmd", "rcmd":
            modifiers.insert(.maskCommand)
        case "ctrl", "control", "lctrl":
            modifiers.insert(.maskControl)
        case "rctrl":
            modifiers.insert(.maskControl)
        case "shift":
            modifiers.insert(.maskShift)
        case "option", "alt":
            modifiers.insert(.maskAlternate)
        default:
            throw KeyParseError.unknownToken(part)
        }
    }

    switch last {
    case "enter", "return":
        return KeyCombo(key: .enter, modifiers: modifiers)
    case "backspace", "delete":
        return KeyCombo(key: .backspace, modifiers: modifiers)
    case "rctrl", "rightcontrol", "right_control":
        return KeyCombo(key: .rightControl, modifiers: modifiers)
    case "z":
        return KeyCombo(key: .z, modifiers: modifiers)
    case "u":
        return KeyCombo(key: .u, modifiers: modifiers)
    case "grave", "backtick", "`":
        return KeyCombo(key: .grave, modifiers: modifiers)
    default:
        throw KeyParseError.unknownToken(last)
    }
}
