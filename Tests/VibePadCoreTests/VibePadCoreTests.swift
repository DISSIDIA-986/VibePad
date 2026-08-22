import XCTest
import Yams
@testable import VibePadCore

final class KeyParseTests: XCTestCase {
    func testRctrl() throws {
        let combo = try parseKeySpec("rctrl")
        XCTAssertEqual(combo.key, .rightControl)
        XCTAssertTrue(combo.modifiers.isEmpty)
    }

    func testCmdZ() throws {
        let combo = try parseKeySpec("cmd+z")
        XCTAssertEqual(combo.key, .z)
        XCTAssertTrue(combo.modifiers.contains(.maskCommand))
    }

    func testCtrlU() throws {
        let combo = try parseKeySpec("ctrl+u")
        XCTAssertEqual(combo.key, .u)
        XCTAssertTrue(combo.modifiers.contains(.maskControl))
    }

    func testUnknown() {
        XCTAssertThrowsError(try parseKeySpec("fn+space"))
    }
}

final class MouseEngineTests: XCTestCase {
    func testDeadzoneZeroesSmallInput() {
        let cfg = MouseMoveConfig(deadzone: 0.18, pollHz: 500)
        let d = MouseEngine.delta(for: StickSample(axisX: 0.1, axisY: 0), config: cfg)
        XCTAssertEqual(d.deltaX, 0)
    }

    func testMaxAxisProducesNonZeroDelta() {
        let cfg = MouseMoveConfig(deadzone: 0.18, pollHz: 500, precisionMultiplier: 1)
        let d = MouseEngine.delta(for: StickSample(axisX: 1.0, axisY: 0), config: cfg)
        XCTAssertGreaterThan(abs(d.deltaX), 0)
    }

    func testPrecisionMultiplier() {
        let cfg = MouseMoveConfig(deadzone: 0, pollHz: 500, precisionMultiplier: 0.25)
        let full = MouseEngine.delta(for: StickSample(axisX: 0.8, axisY: 0), config: cfg, precisionHeld: false)
        let prec = MouseEngine.delta(for: StickSample(axisX: 0.8, axisY: 0), config: cfg, precisionHeld: true)
        XCTAssertEqual(prec.deltaX, full.deltaX * 0.25, accuracy: 0.001)
    }

    func testEmptyStick() {
        let cfg = MouseMoveConfig()
        let d = MouseEngine.delta(for: StickSample(axisX: 0, axisY: 0), config: cfg)
        XCTAssertEqual(d.deltaX, 0)
        XCTAssertEqual(d.deltaY, 0)
    }

    func testNegativeAxis() {
        let cfg = MouseMoveConfig(deadzone: 0, pollHz: 100)
        let d = MouseEngine.delta(for: StickSample(axisX: -1, axisY: 0), config: cfg)
        XCTAssertLessThan(d.deltaX, 0)
    }
}

final class DebounceTests: XCTestCase {
    func testBlocksRapidFire() {
        var d = EdgeDebouncer(intervalMs: 50)
        XCTAssertTrue(d.shouldFire(buttonID: "lb", nowMs: 1000))
        XCTAssertFalse(d.shouldFire(buttonID: "lb", nowMs: 1020))
        XCTAssertTrue(d.shouldFire(buttonID: "lb", nowMs: 1060))
    }

    func testIndependentButtons() {
        var d = EdgeDebouncer(intervalMs: 50)
        XCTAssertTrue(d.shouldFire(buttonID: "a", nowMs: 1000))
        XCTAssertTrue(d.shouldFire(buttonID: "b", nowMs: 1000))
    }
}

final class ConfigTests: XCTestCase {
    func testLoadDefaultShape() throws {
        let yaml = """
        version: 1
        poll_hz: 500
        rules:
          ghostty:
            apps: [com.mitchellh.ghostty]
            buttons:
              lb:
                tap: rctrl
        """
        let config = try YAMLDecoder().decode(VibePadConfig.self, from: yaml)
        XCTAssertEqual(config.version, 1)
        XCTAssertEqual(config.pollHz, 500)
        XCTAssertNotNil(config.profile(matching: "com.mitchellh.ghostty"))
        XCTAssertNil(config.profile(matching: "com.apple.Terminal"))
    }
}
