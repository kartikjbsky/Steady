#!/usr/bin/env python3
"""Create the .icns icon file on macOS using the checked-in PNG master."""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / "src/steady/assets/steady_icon.png"
iconset = ROOT / "packaging/steady.iconset"
out = ROOT / "packaging/steady.icns"

if shutil.which("iconutil") is None:
    raise SystemExit("iconutil is required; this script must run on macOS.")

iconset.mkdir(parents=True, exist_ok=True)
sizes = [16, 32, 128, 256, 512]
for size in sizes:
    for scale in (1, 2):
        px = size * scale
        target = iconset / f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
        subprocess.run(
            ["sips", "-z", str(px), str(px), str(source), "--out", str(target)],
            check=True,
            stdout=subprocess.DEVNULL,
        )
subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True)
shutil.rmtree(iconset, ignore_errors=True)
print(f"Created {out}")
