# Third-party components and distribution notes

Steady uses third-party software. This is a project-level pointer list, not a substitute for the license files shipped by each dependency.

- **PySide6 / Qt for Python** — available under LGPLv3/GPLv3 or a commercial Qt license. Review the terms for the exact Qt modules and wheels included in each binary release. Official information: <https://doc.qt.io/qtforpython-6/> and <https://doc.qt.io/qt-6/licensing.html>.
- **Matplotlib** — distributed under its BSD-compatible license. Review the license corresponding to the exact version bundled by the build.
- **Python** — distributed under the Python Software Foundation License. See <https://docs.python.org/3/license.html>.
- **PyInstaller** — GPLv2-or-later with a bootloader exception; the exception permits distribution of applications bundled from your source code, subject to the licenses of bundled dependencies. See <https://pyinstaller.org/en/stable/license.html>.

The release workflow does not yet perform Windows code signing, Apple Developer ID signing, or macOS notarization. Add those steps and credentials before presenting the binaries as verified publisher builds.

Steady's own source-code license has not been selected yet. Decide whether the project will be MIT, Apache-2.0, GPL, or proprietary before publishing the repository as a public project. Do not assume the third-party dependency licenses automatically choose a license for Steady itself.
