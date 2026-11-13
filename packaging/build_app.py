#!/usr/bin/env python3
"""Build a native, one-folder Steady application for the current OS.

Run this script on the OS you intend to package. PyInstaller bundles are
platform-specific and are not cross-compiled.
"""
from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os_name = platform.system()


def main() -> int:
    if os_name not in {"Linux", "Windows", "Darwin"}:
        raise SystemExit(f"Unsupported build platform: {os_name}")

    if not (ROOT / "src/steady/__main__.py").is_file():
        raise SystemExit("Run from the complete Steady source project.")

    try:
        from PyInstaller.__main__ import run as run_pyinstaller
    except ImportError as exc:
        raise SystemExit(
            "PyInstaller is not installed. Run: python -m pip install -e '.[dev]'"
        ) from exc

    if (ROOT / "build").exists():
        shutil.rmtree(ROOT / "build")

    assets = ROOT / "src/steady/assets"
    schema = ROOT / "src/steady/database/schema.sql"
    icon_png = ROOT / "packaging/steady.png"
    icon_ico = ROOT / "packaging/steady.ico"
    icon_icns = ROOT / "packaging/steady.icns"

    args = [
        str(ROOT / "src/steady/__main__.py"),
        "--name", "Steady",
        "--noconfirm",
        "--clean",
        "--windowed",
        "--onedir",
        "--paths", str(ROOT / "src"),
        "--collect-all", "PySide6.QtMultimedia",
        "--collect-all", "matplotlib",
        "--hidden-import", "PySide6.QtMultimedia",
        "--hidden-import", "matplotlib.backends.backend_qtagg",
        "--add-data", f"{assets}{os.pathsep}steady/assets",
        "--add-data", f"{schema}{os.pathsep}steady/database",
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build/pyinstaller"),
        "--specpath", str(ROOT / "build/spec"),
    ]

    if os_name == "Windows":
        if icon_ico.is_file():
            args.extend(["--icon", str(icon_ico)])
    elif os_name == "Darwin":
        if icon_icns.is_file():
            args.extend(["--icon", str(icon_icns)])
        args.extend(["--osx-bundle-identifier", "app.steadyplanner.desktop"])
    else:
        if icon_png.is_file():
            args.extend(["--icon", str(icon_png)])

    print(f"Building Steady for {os_name} on {platform.machine()}…")
    print("The database is stored in the user's OS application-data directory, not in this bundle.")
    run_pyinstaller(args)

    if os_name == "Darwin":
        expected = ROOT / "dist/Steady.app"
    else:
        expected = ROOT / "dist/Steady"

    if not expected.exists():
        raise SystemExit(f"Build finished but expected output was not found: {expected}")

    print(f"\nBuild successful: {expected}")
    print("Next, run: python packaging/package_release.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
