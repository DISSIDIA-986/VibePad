import Foundation
import Yams

public struct ButtonAction: Sendable, Decodable {
    public var tap: String?
    public var combo: String?

    public func resolvedSpec() throws -> String {
        if let tap { return tap }
        if let combo { return combo }
        throw ConfigError.emptyButtonAction
    }
}

public struct StickConfig: Sendable, Decodable {
    public var mode: String?
    public var deadzone: Double?
    public var gamma: Double?
    public var maxSpeedPxS: Double?

    enum CodingKeys: String, CodingKey {
        case mode, deadzone, gamma
        case maxSpeedPxS = "max_speed_px_s"
    }

    public func mouseMoveConfig(pollHz: Double) -> MouseMoveConfig {
        MouseMoveConfig(
            deadzone: deadzone ?? 0.18,
            gamma: gamma ?? 2.0,
            maxSpeedPxS: maxSpeedPxS ?? 2400,
            pollHz: pollHz
        )
    }
}

public struct ProfileRule: Sendable, Decodable {
    public var apps: [String]
    public var buttons: [String: ButtonAction]?
    public var sticks: [String: StickConfig]?
}

public struct VibePadConfig: Sendable, Decodable {
    public var version: Int
    public var pollHz: Double
    public var rules: [String: ProfileRule]

    enum CodingKeys: String, CodingKey {
        case version
        case pollHz = "poll_hz"
        case rules
    }

    public static func load(from url: URL) throws -> VibePadConfig {
        let text = try String(contentsOf: url, encoding: .utf8)
        let decoder = YAMLDecoder()
        return try decoder.decode(VibePadConfig.self, from: text)
    }

    public func profile(matching bundleID: String) -> ProfileRule? {
        for (_, rule) in rules where rule.apps.contains(bundleID) {
            return rule
        }
        return nil
    }
}

public enum ConfigError: Error, CustomStringConvertible {
    case emptyButtonAction
    case fileNotFound(String)

    public var description: String {
        switch self {
        case .emptyButtonAction:
            return "Button action must specify tap or combo"
        case .fileNotFound(let path):
            return "Config not found: \(path)"
        }
    }
}

public enum ConfigPaths {
    public static var defaultConfigURL: URL {
        let base = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("Library/Application Support/VibePad", isDirectory: true)
        return base.appendingPathComponent("config.yaml")
    }

    public static var bundledDefaultURL: URL? {
        Bundle.main.url(forResource: "default", withExtension: "yaml")
    }
}
