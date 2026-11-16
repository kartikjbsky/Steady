Steady v1.2.0 — logo and feedback-button refinement

This is an overlay patch for the existing Steady v1.2.0 source tree.
It includes the full feature set from the previous integrated v1.2.0 patch,
plus the user's exact full wordmark image and the supplied terracotta feedback
button image. The feedback banner is a large, centred clickable image in Settings.

From the extracted folder, copy the contents of steady_app_patch/ over the
existing repository. Do not replace or delete the user's application-data
directory or SQLite database. Back up the database before upgrading.

After applying:
  source .venv/bin/activate
  python -m pip install -e ".[dev]"
  python -m pytest -q tests/
  python packaging/check_release_metadata.py --require-contact --tag v1.2.0
  python -m steady

The new feedback_form_button.png is part of steady.assets package data and is
included in the PyInstaller application bundle. Platform app icons continue to
use the icon-only steady_icon asset.
