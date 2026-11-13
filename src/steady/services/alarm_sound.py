from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QTimer, QUrl
from PySide6.QtWidgets import QApplication

try:
    from PySide6.QtMultimedia import QSoundEffect
except (ImportError, OSError):  # A system without Qt Multimedia can still use the OS beep.
    QSoundEffect = None  # type: ignore[assignment,misc]


class AlarmSound(QObject):
    """Play Steady's bundled two-pass chime with a system-beep fallback."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._effect = None
        self._pending_play = False
        if QSoundEffect is not None:
            asset = Path(__file__).resolve().parents[1] / "assets" / "steady_alarm.wav"
            if asset.is_file():
                try:
                    self._effect = QSoundEffect(self)
                    self._effect.setSource(QUrl.fromLocalFile(str(asset)))
                    self._effect.setVolume(0.88)
                    # Two short chime passes make an alert noticeable without
                    # turning it into a harsh, continuous alarm.
                    self._effect.setLoopCount(2)
                    self._effect.statusChanged.connect(self._on_status_changed)
                except Exception:
                    self._effect = None

    def play(self) -> None:
        """Play the bundled chime; wait for initial loading when necessary."""
        if self._effect is not None:
            try:
                if self._effect.isLoaded():
                    self._pending_play = False
                    self._effect.stop()
                    self._effect.play()
                    return
                if self._effect.status() != QSoundEffect.Status.Error:
                    # QSoundEffect loads local files asynchronously. Queue an
                    # early alert rather than immediately substituting a beep.
                    self._pending_play = True
                    return
            except RuntimeError:
                self._effect = None
        self._fallback_beep(0)

    def _on_status_changed(self) -> None:
        if not self._pending_play or self._effect is None:
            return
        try:
            if self._effect.isLoaded():
                self._pending_play = False
                self._effect.play()
            elif self._effect.status() == QSoundEffect.Status.Error:
                self._pending_play = False
                self._fallback_beep(0)
        except RuntimeError:
            self._pending_play = False
            self._effect = None
            self._fallback_beep(0)

    @staticmethod
    def _fallback_beep(index: int) -> None:
        QApplication.beep()
        if index < 1:
            QTimer.singleShot(260, lambda: AlarmSound._fallback_beep(index + 1))
