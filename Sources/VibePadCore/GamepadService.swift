import Foundation
import GameController

public enum GamepadServiceError: Error, CustomStringConvertible {
    case noController

    public var description: String {
        switch self {
        case .noController:
            return "No game controller connected"
        }
    }
}

public struct GamepadButton: Sendable {
    public let id: String
    public let pressed: Bool
}

public final class GamepadService: @unchecked Sendable {
    private var controller: GCController?
    public var onButtonEdge: ((GamepadButton) -> Void)?
    public var onStick: ((String, StickSample) -> Void)?
    public var verbose: Bool = false

    private var previousButtons: [String: Bool] = [:]
    private var pollTimer: Timer?
    private var loggedNoController = false

    public init(verbose: Bool = false) {
        self.verbose = verbose
        GCController.shouldMonitorBackgroundEvents = true
        GCController.startWirelessControllerDiscovery(completionHandler: nil)
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(controllerConnected),
            name: .GCControllerDidConnect,
            object: nil
        )
        NotificationCenter.default.addObserver(
            self,
            selector: #selector(controllerDisconnected),
            name: .GCControllerDidDisconnect,
            object: nil
        )
        bindFirstController(force: false)
        pollTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            self?.pollForController()
        }
    }

    deinit {
        pollTimer?.invalidate()
        GCController.stopWirelessControllerDiscovery()
    }

    public var controllerName: String {
        controller?.vendorName ?? "none"
    }

    public func isConnected() -> Bool {
        controller != nil
    }

    @objc private func controllerConnected(_ note: Notification) {
        if verbose {
            let name = (note.object as? GCController)?.vendorName ?? "?"
            fputs("[vibepad] GCController connected: \(name)\n", stderr)
        }
        bindFirstController(force: true)
    }

    @objc private func controllerDisconnected(_ note: Notification) {
        if let disconnected = note.object as? GCController, disconnected == controller {
            controller = nil
            previousButtons = [:]
        }
        bindFirstController(force: true)
    }

    private func pollForController() {
        if controller == nil {
            bindFirstController(force: false)
        }
    }

    private func bindFirstController(force: Bool) {
        if controller != nil && !force { return }
        guard let next = GCController.controllers().first else {
            if verbose && !loggedNoController {
                fputs("[vibepad] no GCController yet — wake Xbox (logo button), ensure Bluetooth connected\n", stderr)
                loggedNoController = true
            }
            return
        }
        loggedNoController = false
        if controller === next { return }
        controller = next
        previousButtons = [:]
        fputs("[vibepad] bound controller: \(next.vendorName ?? "unknown")\n", stderr)
        guard let pad = next.extendedGamepad else {
            fputs("[vibepad] warning: no extendedGamepad profile\n", stderr)
            return
        }

        pad.buttonA.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "a", pressed: pressed)
        }
        pad.buttonB.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "b", pressed: pressed)
        }
        pad.buttonX.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "x", pressed: pressed)
        }
        pad.buttonY.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "y", pressed: pressed)
        }
        pad.leftShoulder.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "lb", pressed: pressed)
        }
        pad.rightShoulder.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "rb", pressed: pressed)
        }
        pad.leftTrigger.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "lt", pressed: pressed)
        }
        pad.rightTrigger.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "rt", pressed: pressed)
        }
        pad.dpad.up.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "dpad_up", pressed: pressed)
        }
        pad.dpad.down.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "dpad_down", pressed: pressed)
        }
        pad.dpad.left.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "dpad_left", pressed: pressed)
        }
        pad.dpad.right.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "dpad_right", pressed: pressed)
        }
        pad.buttonMenu.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "start", pressed: pressed)
        }
        pad.buttonOptions?.pressedChangedHandler = { [weak self] _, _, pressed in
            self?.emitEdge(id: "back", pressed: pressed)
        }
    }

    public func pollSticks() {
        guard let pad = controller?.extendedGamepad else { return }
        let left = StickSample(axisX: Double(pad.leftThumbstick.xAxis.value), axisY: Double(pad.leftThumbstick.yAxis.value))
        onStick?("left", left)
        let right = StickSample(axisX: Double(pad.rightThumbstick.xAxis.value), axisY: Double(pad.rightThumbstick.yAxis.value))
        onStick?("right", right)
    }

    private func emitEdge(id: String, pressed: Bool) {
        let was = previousButtons[id, default: false]
        previousButtons[id] = pressed
        guard pressed && !was else { return }
        if verbose {
            fputs("[vibepad] button edge: \(id)\n", stderr)
        }
        onButtonEdge?(GamepadButton(id: id, pressed: true))
    }
}
