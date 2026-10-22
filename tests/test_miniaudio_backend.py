import wave

import numpy as np
import pytest

from musikkspelar.audio.miniaudio_backend import SAMPLE_RATE, MiniaudioBackend

BLOCK = 300  # rammer per førespurnad, som lydeininga ville bede om


def write_wav(path, value, frames):
    """Writes a stereo WAV file where every sample has the same value (-1.0 to 1.0)."""
    samples = np.full(frames * 2, int(value * 32768), dtype=np.int16)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(samples.tobytes())
    return path


@pytest.fixture
def backend():
    backend = MiniaudioBackend(start_device=False)
    backend.events = []
    backend.on_track_started_automatically = lambda: backend.events.append("next")
    backend.on_playback_finished = lambda: backend.events.append("finished")
    feed = backend._feed()
    next(feed)
    backend.pull = lambda frames=BLOCK: feed.send(frames)[:, 0]  # venstre kanal held
    yield backend
    backend.close()


def test_tracks_follow_each_other_without_a_gap(backend, tmp_path):
    backend.play(write_wav(tmp_path / "a.wav", 0.5, 1000))
    backend.set_next(write_wav(tmp_path / "b.wav", -0.5, 1000))
    audio = np.concatenate([backend.pull() for _ in range(8)])
    # Akkurat 1000 rammer av a, rett etterfølgt av 1000 rammer av b, så stille
    assert np.all(audio[:1000] == 0.5)
    assert np.all(audio[1000:2000] == -0.5)
    assert np.all(audio[2000:] == 0)
    assert backend.events == ["next", "finished"]


def test_volume_scales_the_signal(backend, tmp_path):
    backend.play(write_wav(tmp_path / "a.wav", 0.5, 1000))
    backend.volume = 50
    assert np.allclose(backend.pull(), 0.5 * 0.25)


def test_pause_gives_silence_and_keeps_position(backend, tmp_path):
    backend.play(write_wav(tmp_path / "a.wav", 0.5, 1000))
    backend.pull()
    backend.paused = True
    position = backend.position
    assert np.all(backend.pull() == 0)
    assert backend.position == position


def test_seek_continues_from_new_position(backend, tmp_path):
    backend.play(write_wav(tmp_path / "a.wav", 0.5, SAMPLE_RATE * 2))
    backend.seek(1.5, absolute=True)
    assert backend.duration == pytest.approx(2.0)
    remaining = sum(np.count_nonzero(backend.pull()) for _ in range(400))
    assert remaining == pytest.approx(SAMPLE_RATE * 0.5, abs=2)


def test_unreadable_file_reports_finished(backend, tmp_path):
    broken = tmp_path / "broken.mp3"
    broken.write_bytes(b"not audio")
    backend.play(broken)
    assert backend.events == ["finished"]
    assert backend.position is None
