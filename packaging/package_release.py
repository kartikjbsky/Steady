#!/usr/bin/env python3
"""Create a user-facing archive from the current OS PyInstaller build."""
from __future__ import annotations

import hashlib
import platform
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
RELEASE = ROOT / "release"
sys.path.insert(0, str(ROOT / "src"))
from steady.app_info import APP_VERSION as VERSION  # single editable version source


def zip_directory(source: Path, destination: Path, archive_root: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED, compresslevel=8) as archive:
        for file in source.rglob("*"):
            if file.is_file():
                archive.write(file, Path(archive_root) / file.relative_to(source))


def main() -> int:
    system = platform.system()
    RELEASE.mkdir(exist_ok=True)
    for item in RELEASE.iterdir():
        if item.is_dir():
            shutil.rmtree(item)
        else:
            item.unlink()

    if system == "Windows":
        built = DIST / "Steady"
        if not (built / "Steady.exe").is_file():
            raise SystemExit(f"Expected Windows executable not found: {built / 'Steady.exe'}")
        package_dir = RELEASE / "Steady-Windows-x64"
        shutil.copytree(built, package_dir)
        shutil.copy2(ROOT / "packaging/windows/Create-Shortcut.ps1", package_dir)
        shutil.copy2(ROOT / "packaging/windows/README-FIRST.txt", package_dir)
        archive = RELEASE / f"Steady-{VERSION}-Windows-x64.zip"
        zip_directory(package_dir, archive, package_dir.name)
        shutil.rmtree(package_dir)

    elif system == "Darwin":
        built = DIST / "Steady.app"
        if not built.is_dir():
            raise SystemExit(f"Expected macOS application bundle not found: {built}")
        archive = RELEASE / f"Steady-{VERSION}-macOS-{platform.machine()}.zip"
        subprocess.run(
            ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(built), str(archive)],
            check=True,
        )
        (RELEASE / "README-macOS-FIRST.txt").write_text(
            "Open Steady.app. For a manual install, drag it into Applications.\n\n"
            "This build is not Developer ID signed or notarized. macOS Gatekeeper may show\n"
            "a first-launch warning. For public distribution, configure Apple signing and\n"
            "notarization credentials in the release workflow.\n\n"
            "Your database and backups live outside the app bundle in your user Library.\n",
            encoding="utf-8",
        )

    elif system == "Linux":
        built = DIST / "Steady"
        if not (built / "Steady").is_file():
            raise SystemExit(f"Expected Linux executable not found: {built / 'Steady'}")
        package_dir = RELEASE / "Steady-Linux-x86_64"
        package_dir.mkdir(parents=True)
        shutil.copytree(built, package_dir / "app")
        shutil.copy2(ROOT / "packaging/linux/install.sh", package_dir / "install.sh")
        shutil.copy2(ROOT / "packaging/linux/uninstall.sh", package_dir / "uninstall.sh")
        shutil.copy2(ROOT / "packaging/steady.png", package_dir / "steady.png")
        (package_dir / "README-FIRST.txt").write_text(
            "STEADY FOR LINUX (x86_64)\n\n"
            "Quick install:\n"
            "  1. Extract this archive.\n"
            "  2. Open a terminal in the extracted folder.\n"
            "  3. Run: ./install.sh\n"
            "  4. Launch Steady from your desktop application menu.\n\n"
            "Portable run (without installing a menu entry): ./app/Steady\n\n"
            "To remove the application files: ./uninstall.sh\n"
            "Your personal database and backups are not removed by uninstall.sh.\n",
            encoding="utf-8",
        )
        archive = RELEASE / f"Steady-{VERSION}-Linux-x86_64.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(package_dir, arcname=package_dir.name)
        shutil.rmtree(package_dir)
    else:
        raise SystemExit(f"Unsupported packaging platform: {system}")

    # Checksums use a platform-specific filename so matrix builds never
    # overwrite one another when GitHub Actions merges release artifacts.
    machine = platform.machine().replace(" ", "_")
    platform_key = {
        "Windows": "Windows-x64",
        "Darwin": f"macOS-{machine}",
        "Linux": "Linux-x86_64",
    }[system]
    artifacts = sorted(
        path for path in RELEASE.iterdir()
        if path.is_file() and not path.name.startswith("SHA256SUMS-")
    )
    lines = []
    for artifact in artifacts:
        digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
        lines.append(f"{digest}  {artifact.name}")
    (RELEASE / f"SHA256SUMS-{platform_key}.txt").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )

    print("Release files:")
    for path in sorted(RELEASE.iterdir()):
        if path.is_file():
            print(f"  {path.name} ({path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
