import Foundation

public struct EdgeDebouncer: Sendable {
    private let intervalMs: Int
    private var lastFireMs: [String: Int64] = [:]

    public init(intervalMs: Int = 50) {
        self.intervalMs = intervalMs
    }

    public mutating func shouldFire(buttonID: String, nowMs: Int64) -> Bool {
        if let last = lastFireMs[buttonID], nowMs - last < intervalMs {
            return false
        }
        lastFireMs[buttonID] = nowMs
        return true
    }
}
