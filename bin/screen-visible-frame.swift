#!/usr/bin/env swift
// Union of every connected display's visibleFrame (multi-monitor + AR glasses).
import AppKit

let screens = NSScreen.screens
guard let first = screens.first else {
    print("0 0 0 1920 1080")
    exit(0)
}

var union = first.visibleFrame
for screen in screens.dropFirst() {
    union = union.union(screen.visibleFrame)
}

// screen_count x y width height
print("\(screens.count) \(union.origin.x) \(union.origin.y) \(union.size.width) \(union.size.height)")
