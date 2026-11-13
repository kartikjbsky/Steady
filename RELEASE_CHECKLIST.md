# Steady 1.0.0 release checklist

- [ ] Set `CONTACT_EMAIL` in `src/steady/app_info.py` to the intended public address.
- [ ] Confirm `AUTHOR_NAME` is displayed exactly as desired.
- [ ] Choose and add a license for Steady's own source before making the repository public.
- [ ] Review `THIRD_PARTY_NOTICES.md`, especially the PySide6 / Qt for Python LGPLv3/GPLv3 or commercial licensing terms.
- [ ] Run `python -m pytest -q`.
- [ ] Build/test Linux x86_64, Windows x64, macOS Apple Silicon and macOS Intel artifacts.
- [ ] Test first launch, database creation, alarm sound, theme switching and backup/restore on each OS.
- [ ] Configure Windows Authenticode signing if distributing to a broad Windows audience.
- [ ] Configure Apple Developer ID signing and notarization for macOS public distribution.
- [ ] Create and push a version tag such as `v1.0.0` to trigger the release workflow.
- [ ] Keep a backup of the live SQLite database before updating an existing installation.
