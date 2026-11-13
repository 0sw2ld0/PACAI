// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "PACAI",
    platforms: [.macOS(.v14), .iOS(.v17)],
    products: [
        .library(name: "PACAI", targets: ["PACAI"]),
    ],
    targets: [
        .target(name: "PACAI"),
        .testTarget(name: "PACAITests", dependencies: ["PACAI"]),
    ]
)
