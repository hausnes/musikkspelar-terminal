import threading
from collections import OrderedDict

import miniaudio
import numpy as np


class SpectrumAnalyzer:
    """Computes the frequency spectrum of a track at a given point in time.

    mpv does not give us the audio it plays, so each track is decoded a
    second time (to mono, at a low sample rate) in a background thread.
    The spectrum is then computed for the samples around the position mpv
    reports, which keeps the visualisation in sync with what we hear."""

    SAMPLE_RATE = 22050
    FFT_SIZE = 2048           # ~93 ms med lyd per utrekning
    LOWEST_FREQUENCY = 40     # Hz
    HIGHEST_FREQUENCY = 10000
    DB_FLOOR = -70            # alt svakare enn dette blir ei tom søyle
    DB_CEILING = -10
    TILT_PER_OCTAVE = 3.0     # dB: løftar diskanten, som elles ser kunstig låg ut
    CACHE_SIZE = 3            # gjeldande låt, neste låt og éi ekstra

    def __init__(self):
        self._cache = OrderedDict()  # path -> np.ndarray (int16), eller None om fila ikkje kunne dekodast
        self._loading = set()
        self._lock = threading.Lock()
        self._window = np.hanning(self.FFT_SIZE).astype(np.float32)
        self._frequencies = np.fft.rfftfreq(self.FFT_SIZE, 1 / self.SAMPLE_RATE)
        self._band_edges = {}  # tal på band -> bin-indeksar, rekna ut ved behov

    # --- Dekoding ------------------------------------------------------

    def prepare(self, path):
        """Starts decoding the file in the background, unless it is already done."""
        with self._lock:
            if path in self._cache or path in self._loading:
                return
            self._loading.add(path)
        threading.Thread(target=self._decode, args=(path,), daemon=True).start()

    def _decode(self, path):
        try:
            decoded = miniaudio.decode_file(
                str(path),
                output_format=miniaudio.SampleFormat.SIGNED16,
                nchannels=1,
                sample_rate=self.SAMPLE_RATE,
            )
            samples = np.frombuffer(decoded.samples, dtype=np.int16)
        except (miniaudio.DecodeError, OSError):
            samples = None  # t.d. formatet støttast ikkje av miniaudio
        with self._lock:
            self._loading.discard(path)
            self._cache[path] = samples
            while len(self._cache) > self.CACHE_SIZE:
                self._cache.popitem(last=False)

    # --- Spekter -------------------------------------------------------

    def _edges_for(self, bands):
        """Splits the frequency range into bands spaced evenly on a log scale.

        Returns a list of (first bin, last bin + 1, centre frequency)."""
        if bands not in self._band_edges:
            limits = np.geomspace(self.LOWEST_FREQUENCY, self.HIGHEST_FREQUENCY, bands + 1)
            bins = np.searchsorted(self._frequencies, limits)
            edges = []
            for i in range(bands):
                low = bins[i]
                high = max(bins[i + 1], low + 1)  # dei lågaste banda er smalare enn éin bin
                edges.append((low, high, np.sqrt(limits[i] * limits[i + 1])))
            self._band_edges[bands] = edges
        return self._band_edges[bands]

    def levels(self, path, position, bands):
        """Returns an array with one level (0.0–1.0) per band, or None if the
        track is not decoded (yet)."""
        with self._lock:
            samples = self._cache.get(path)
            if path in self._cache:
                self._cache.move_to_end(path)
        if samples is None or position is None:
            return None

        end = int(position * self.SAMPLE_RATE)
        start = end - self.FFT_SIZE
        if end <= 0 or start >= len(samples):
            return np.zeros(bands)
        chunk = samples[max(start, 0):end].astype(np.float32) / 32768
        if len(chunk) < self.FFT_SIZE:
            chunk = np.pad(chunk, (self.FFT_SIZE - len(chunk), 0))

        # Normalisert slik at ein sinus med full styrke gir 0 dB
        magnitudes = np.abs(np.fft.rfft(chunk * self._window)) / (self.FFT_SIZE / 4)

        result = np.empty(bands)
        for i, (low, high, centre) in enumerate(self._edges_for(bands)):
            db = 20 * np.log10(magnitudes[low:high].max() + 1e-9)
            db += self.TILT_PER_OCTAVE * np.log2(centre / 1000)
            result[i] = (db - self.DB_FLOOR) / (self.DB_CEILING - self.DB_FLOOR)
        return np.clip(result, 0.0, 1.0)
