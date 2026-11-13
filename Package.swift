// swift-tools-version: 6.0
import PackageDescription

let package = Package(
    name: "MyModem",
    platforms: [.macOS(.v14)],
    products: [
        .executable(name: "MyModem", targets: ["MyModemApp"])
    ],
    targets: [
        .executableTarget(
            name: "MyModemApp",
            path: "Sources/MyModemApp",
            swiftSettings: [
                .enableUpcomingFeature("ExistentialAny")
            ]
        ),
        .testTarget(
            name: "MyModemTests",
            dependencies: ["MyModemApp"],
            path: "Tests/MyModemTests"
        )
    ]
)
