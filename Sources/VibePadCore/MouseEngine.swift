import Foundation

public struct StickSample: Sendable {
    public let axisX: Double
    public let axisY: Double

    public init(axisX: Double, axisY: Double) {
        self.axisX = axisX
        self.axisY = axisY
    }
}

public struct MouseMoveConfig: Sendable {
    public var deadzone: Double
    public var gamma: Double
    public var maxSpeedPxS: Double
    public var pollHz: Double
    public var precisionMultiplier: Double

    public init(
        deadzone: Double = 0.18,
        gamma: Double = 2.0,
        maxSpeedPxS: Double = 2400,
        pollHz: Double = 500,
        precisionMultiplier: Double = 0.25
    ) {
        self.deadzone = deadzone
        self.gamma = gamma
        self.maxSpeedPxS = maxSpeedPxS
        self.pollHz = pollHz
        self.precisionMultiplier = precisionMultiplier
    }
}

public struct MouseDelta: Sendable {
    public let deltaX: Double
    public let deltaY: Double

    public init(deltaX: Double, deltaY: Double) {
        self.deltaX = deltaX
        self.deltaY = deltaY
    }
}

public enum MouseEngine {
    /// normalized = max(0, (abs(axis) - deadzone) / (1 - deadzone))
    /// speed = maxSpeed * pow(normalized, gamma) * sign(axis)
    /// delta = speed / pollHz
    public static func delta(
        for sample: StickSample,
        config: MouseMoveConfig,
        precisionHeld: Bool = false
    ) -> MouseDelta {
        let mult = precisionHeld ? config.precisionMultiplier : 1.0
        return MouseDelta(
            deltaX: axisDelta(sample.axisX, config: config) * mult,
            deltaY: axisDelta(-sample.axisY, config: config) * mult
        )
    }

    private static func axisDelta(_ axis: Double, config: MouseMoveConfig) -> Double {
        let magnitude = abs(axis)
        guard magnitude > config.deadzone else { return 0 }
        let normalized = (magnitude - config.deadzone) / (1.0 - config.deadzone)
        let speed = config.maxSpeedPxS * pow(normalized, config.gamma) * (axis >= 0 ? 1 : -1)
        return speed / config.pollHz
    }
}
