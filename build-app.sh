#!/bin/bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
APP="$ROOT/dist/MyModem.app"
CONTENTS="$APP/Contents"
BINARY="$ROOT/.build/release/MyModem"

cd "$ROOT"
swift build -c release -Xswiftc -warnings-as-errors
rm -rf "$APP"
mkdir -p "$CONTENTS/MacOS" "$CONTENTS/Resources"
cp "$BINARY" "$CONTENTS/MacOS/MyModem"
cp "$ROOT/Assets/MyModem.icns" "$CONTENTS/Resources/MyModem.icns"

cat > "$CONTENTS/Info.plist" <<'PLIST'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>CFBundleExecutable</key><string>MyModem</string>
  <key>CFBundleIdentifier</key><string>ir.matinsojoudi.mymodem</string>
  <key>CFBundleName</key><string>MyModem</string>
  <key>CFBundleDisplayName</key><string>MyModem</string>
  <key>CFBundleIconFile</key><string>MyModem</string>
  <key>CFBundlePackageType</key><string>APPL</string>
  <key>CFBundleShortVersionString</key><string>2.4.0</string>
  <key>CFBundleVersion</key><string>20400</string>
  <key>LSMinimumSystemVersion</key><string>14.0</string>
  <key>NSHighResolutionCapable</key><true/>
  <key>NSLocalNetworkUsageDescription</key><string>MyModem برای دریافت وضعیت، پیامک و مدیریت دستگاه‌ها به مودم شبکه محلی متصل می‌شود.</string>
  <key>NSAppTransportSecurity</key><dict>
    <key>NSAllowsLocalNetworking</key><true/>
    <key>NSAllowsArbitraryLoads</key><true/>
  </dict>
</dict></plist>
PLIST

codesign --force --deep --sign - "$APP"
echo "$APP"
