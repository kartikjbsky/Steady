#!/usr/bin/env bash
set -euo pipefail
rm -rf "$HOME/.local/opt/steady"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/applications/steady.desktop"
rm -f "${XDG_DATA_HOME:-$HOME/.local/share}/icons/steady.png"
echo "Steady application files removed. Your personal database and backups were not deleted."
