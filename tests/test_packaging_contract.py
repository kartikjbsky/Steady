from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_build_scripts_create_native_onedir_packages():
    build = (ROOT / "packaging" / "build_app.py").read_text(encoding="utf-8")
    release = (ROOT / "packaging" / "package_release.py").read_text(encoding="utf-8")
    assert '"--onedir"' in build
    assert '"--windowed"' in build
    assert "os.pathsep" in build
    assert '"Steady.app"' in release
    assert '"Steady.exe"' in release
    assert '"Steady-Linux-x86_64"' in release


def test_all_native_assets_are_present():
    assert (ROOT / "src/steady/assets/steady_icon.png").is_file()
    assert (ROOT / "packaging/steady.ico").is_file()
    assert (ROOT / "packaging/steady.svg").is_file()
    assert (ROOT / "packaging/steady.png").is_file()


def test_cross_platform_release_matrix_is_configured():
    workflow = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
    for runner in ("ubuntu-22.04", "windows-latest", "macos-15", "macos-15-intel"):
        assert runner in workflow
    assert "softprops/action-gh-release@v3.0.3" in workflow
    assert "--require-contact" in workflow


def test_linux_install_does_not_remove_user_database():
    uninstall = (ROOT / "packaging/linux/uninstall.sh").read_text(encoding="utf-8")
    assert ".local/opt/steady" in uninstall
    assert "steady.sqlite3" not in uninstall
    assert 'rm -rf "$HOME/.local/opt/steady"' in uninstall
    assert 'rm -rf "$HOME/.local/share/steady"' not in uninstall
