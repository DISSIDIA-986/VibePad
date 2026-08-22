#!/bin/zsh
# Build VibePad.app menu-bar bundle (Phase 1 scaffold).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
APP="$REPO/VibePad.app"
BIN="$APP/Contents/MacOS/VibePad"
ICON="$REPO/config/VibePadApp/AppIcon.icns"

echo "Building VibePadApp..."
(cd "$REPO" && swift build -c release --product VibePadApp)

if [[ ! -f "$ICON" ]]; then
  echo "Building app icon..."
  "$REPO/bin/build-icon.sh"
fi

rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$REPO/config/VibePadApp/Info.plist" "$APP/Contents/Info.plist"
cp "$ICON" "$APP/Contents/Resources/AppIcon.icns"
cp "$REPO/.build/release/VibePadApp" "$BIN"
chmod +x "$BIN"

echo ""
echo "Built: $APP"
echo "Run:   open \"$APP\""
echo ""
echo "Grant Accessibility to VibePad in System Settings."
echo "Spike launchd daemon remains the production input path until GameController is verified in-app."
