#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SOURCE="$SOURCE_DIR/app"
APP_DIR="$HOME/.local/opt/steady"
ICON_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/icons"
DESKTOP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/applications"

if [[ ! -x "$APP_SOURCE/Steady" ]]; then
  echo "Steady executable not found in: $APP_SOURCE" >&2
  exit 1
fi

mkdir -p "$APP_DIR" "$ICON_DIR" "$DESKTOP_DIR"
cp -a "$APP_SOURCE/." "$APP_DIR/"
install -m 644 "$SOURCE_DIR/steady.png" "$ICON_DIR/steady.png"

cat > "$DESKTOP_DIR/steady.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Steady
Comment=Offline personal planner and focus companion
Exec="$APP_DIR/Steady"
Icon=$ICON_DIR/steady.png
Terminal=false
Categories=Office;Education;Utility;
StartupNotify=true
EOF
chmod 644 "$DESKTOP_DIR/steady.desktop"

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "$DESKTOP_DIR" >/dev/null 2>&1 || true
fi

echo "Steady installed. Open it from your application menu or run: $APP_DIR/Steady"
