from pathlib import Path
import wave


def test_bundled_alarm_is_valid_pcm_wave_file() -> None:
    asset = (
        Path(__file__).parents[1]
        / "src"
        / "steady"
        / "assets"
        / "steady_alarm.wav"
    )
    assert asset.is_file()
    with wave.open(str(asset), "rb") as audio:
        assert audio.getnchannels() == 1
        assert audio.getsampwidth() == 2
        assert audio.getframerate() == 44100
        assert audio.getnframes() > 20000
