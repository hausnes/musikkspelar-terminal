import threading

import miniaudio
import numpy as np

from .backend import AudioBackend

SAMPLE_RATE = 44100
CHANNELS = 2
BUFFER_MSEC = 100
# Lyden vi har levert ligg ei stund i bufferen før han blir høyrd. Posisjonen
# blir justert for dette, så tida og spekteret følgjer det ein faktisk høyrer.
LATENCY = BUFFER_MSEC / 1000


class _Source:
    """One open audio file, decoded bit by bit to float32 stereo at SAMPLE_RATE."""

    def __init__(self, path, start_seconds=0.0):
        self.path = path
        self.duration = miniaudio.get_file_info(str(path)).duration
        start_frame = max(int(start_seconds * SAMPLE_RATE), 0)
        self._stream = miniaudio.stream_file(
            str(path),
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=CHANNELS,
            sample_rate=SAMPLE_RATE,
            seek_frame=start_frame,
        )
        self.frames_read = start_frame

    def read(self, frames):
        """Returns up to frames frames as a (n, CHANNELS) array. Fewer means the file has ended."""
        try:
            chunk = self._stream.send(frames)
        except StopIteration:
            return np.zeros((0, CHANNELS), dtype=np.float32)
        samples = np.frombuffer(chunk, dtype=np.float32).reshape(-1, CHANNELS)
        self.frames_read += len(samples)
        return samples

    def close(self):
        self._stream.close()


class MiniaudioBackend(AudioBackend):
    """Plays audio with miniaudio. Needs nothing but pip packages.

    miniaudio asks for more sound through a generator (_feed) that runs in
    the audio thread. It reads from the current file, and when that file
    ends it carries straight on with the next one in the same buffer, so
    there is no gap between tracks."""

    # miniaudio har innebygde dekodarar for desse formata
    SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".wav"}

    def __init__(self, start_device=True):
        """start_device=False creates the backend without an audio device (for tests)."""
        super().__init__()
        self._lock = threading.Lock()  # vernar _current og _next mot lydtråden
        self._current = None
        self._next = None
        self._next_path = None
        self._paused = False
        self._volume = 100
        self._finished_reported = True
        self._device = None
        if start_device:
            self._start_device()

    def _start_device(self):
        self._device = miniaudio.PlaybackDevice(
            output_format=miniaudio.SampleFormat.FLOAT32,
            nchannels=CHANNELS,
            sample_rate=SAMPLE_RATE,
            buffersize_msec=BUFFER_MSEC,
            app_name="Musikkspelar",
        )
        feed = self._feed()
        next(feed)  # generatoren må startast før miniaudio får han
        self._device.start(feed)

    # --- Lydtråden ------------------------------------------------------

    def _feed(self):
        """Generator that miniaudio sends the number of frames it needs, and
        that yields exactly that many frames back."""
        frames = yield b""
        while True:
            with self._lock:
                output, events = self._fill(frames)
            # Callbackane blir kalla utan låsen, så Player kan kalle tilbake til oss
            for event in events:
                event()
            frames = yield output

    def _fill(self, frames):
        """Builds the next block of audio. Called from the audio thread with the lock held."""
        silence = np.zeros((frames, CHANNELS), dtype=np.float32)
        if self._paused or self._current is None:
            return silence, []

        events = []
        parts = []
        missing = frames
        while missing > 0 and self._current is not None:
            samples = self._current.read(missing)
            parts.append(samples)
            missing -= len(samples)
            if missing > 0:
                # Fila er slutt: hald fram med neste fil i same blokk (gapless)
                self._current.close()
                self._current = self._next
                self._next = None
                self._next_path = None
                if self._current is not None:
                    events.append(self.on_track_started_automatically)

        if self._current is None and not self._finished_reported:
            self._finished_reported = True
            events.append(self.on_playback_finished)

        if missing > 0:
            parts.append(silence[:missing])
        output = np.concatenate(parts) if len(parts) > 1 else parts[0]
        gain = (self._volume / 100) ** 2  # kvadratisk: høyrest jamnare ut enn lineært
        return output * gain, events

    # --- AudioBackend --------------------------------------------------

    def play(self, path):
        try:
            source = _Source(path)
        except (miniaudio.DecodeError, OSError):
            source = None
        with self._lock:
            old, self._current = self._current, source
            self._discard_next()
            self._paused = False
            self._finished_reported = source is None  # ei låt som ikkje kunne opnast, blir meldt under
        if old is not None:
            old.close()
        if source is None:
            self.on_playback_finished()  # fila kunne ikkje opnast

    def set_next(self, path):
        with self._lock:
            if path == self._next_path:
                return
            self._discard_next()
        source = None
        if path is not None:
            try:
                source = _Source(path)  # opnar fila no, så overgangen blir saumlaus
            except (miniaudio.DecodeError, OSError):
                source = None
        with self._lock:
            self._next, self._next_path = source, path

    def _discard_next(self):
        """Closes the preloaded next file. Call with the lock held."""
        if self._next is not None:
            self._next.close()
        self._next = None
        self._next_path = None

    def stop(self):
        with self._lock:
            if self._current is not None:
                self._current.close()
            self._current = None
            self._discard_next()
            self._finished_reported = True

    @property
    def paused(self):
        return self._paused

    @paused.setter
    def paused(self, value):
        self._paused = bool(value)

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, value):
        self._volume = max(0, min(100, int(value)))

    @property
    def position(self):
        current = self._current
        if current is None:
            return None
        return max(current.frames_read / SAMPLE_RATE - LATENCY, 0.0)

    @property
    def duration(self):
        current = self._current
        return current.duration if current is not None else None

    def seek(self, seconds, absolute=False):
        with self._lock:
            current = self._current
        if current is None:
            return
        target = seconds if absolute else (self.position or 0) + seconds
        target = min(max(target, 0.0), current.duration)
        # miniaudio kan berre spole når ei fil blir opna, så vi opnar ho på nytt
        try:
            source = _Source(current.path, start_seconds=target)
        except (miniaudio.DecodeError, OSError):
            return
        with self._lock:
            if self._current is current:
                self._current = source
            else:
                source.close()  # ei anna låt starta medan vi opna fila
                source = None
        if source is not None:
            current.close()

    def close(self):
        if self._device is not None:
            self._device.close()
        self.stop()
