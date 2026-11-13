#!/usr/bin/env python3
"""Validate public metadata and optionally ensure the pushed tag matches it."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from steady.app_info import APP_VERSION, AUTHOR_NAME, CONTACT_EMAIL

parser = argparse.ArgumentParser()
parser.add_argument("--require-contact", action="store_true")
parser.add_argument("--tag", default="")
args = parser.parse_args()

if not AUTHOR_NAME.strip():
    raise SystemExit("AUTHOR_NAME is blank in src/steady/app_info.py")
if args.require_contact and not CONTACT_EMAIL.strip():
    raise SystemExit("Set CONTACT_EMAIL in src/steady/app_info.py before creating a public release.")
if CONTACT_EMAIL and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", CONTACT_EMAIL.strip()):
    raise SystemExit("CONTACT_EMAIL does not look like a valid email address.")
if args.tag:
    expected = args.tag.removeprefix("v")
    if expected != APP_VERSION:
        raise SystemExit(f"Tag {args.tag} does not match APP_VERSION {APP_VERSION} in app_info.py")

print(f"Release metadata OK: Steady {APP_VERSION} by {AUTHOR_NAME}")
if CONTACT_EMAIL:
    print(f"Public contact: {CONTACT_EMAIL}")
else:
    print("Warning: CONTACT_EMAIL is not configured; local builds are allowed, public release validation is not.")
