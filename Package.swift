// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "VibePad",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "vibepad", targets: ["vibepad"]),
        .executable(name: "VibePadApp", targets: ["VibePadApp"]),
        .library(name: "VibePadCore", targets: ["VibePadCore"]),
    ],
    dependencies: [
        .package(url: "https://github.com/jpsim/Yams.git", from: "5.1.0"),
    ],
    targets: [
        .target(
            name: "VibePadCore",
            dependencies: ["Yams"]
        ),
        .executableTarget(
            name: "vibepad",
            dependencies: ["VibePadCore"]
        ),
        .executableTarget(
            name: "VibePadApp",
            dependencies: ["VibePadCore"]
        ),
        .testTarget(
            name: "VibePadCoreTests",
            dependencies: ["VibePadCore"]
        ),
    ]
)
