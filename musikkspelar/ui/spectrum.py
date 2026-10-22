import time

import numpy as np
from rich.color import Color
from rich.segment import Segment
from rich.style import Style
from textual.strip import Strip
from textual.widget import Widget

BLOCKS = " ▁▂▃▄▅▆▇█"  # 1/8-delar av ei rute, for jamnare søyler
PEAK = "▔"

# Klassisk Winamp-gradient, frå botn til topp
GRADIENT = [(0.0, (40, 200, 60)), (0.55, (230, 220, 40)), (1.0, (230, 40, 30))]


def _gradient_color(fraction):
    """Returns the colour at fraction (0.0 = bottom, 1.0 = top) of the gradient."""
    for (low, low_rgb), (high, high_rgb) in zip(GRADIENT, GRADIENT[1:]):
        if fraction <= high:
            t = (fraction - low) / (high - low)
            return Color.from_rgb(*(a + (b - a) * t for a, b in zip(low_rgb, high_rgb)))
    return Color.from_rgb(*GRADIENT[-1][1])


class SpectrumView(Widget):
    """A spectrum analyser in the style of Winamp: bars with falling peaks.

    source(bands) is called every frame and should return an array of levels
    (0.0–1.0), or None when nothing is playing. The bars then fall to zero."""

    DEFAULT_CSS = """
    SpectrumView { height: 1fr; min-height: 4; }
    """

    FPS = 30
    BAR_WIDTH = 2
    GAP = 1
    FALL_SPEED = 2.2       # søylehøgder per sekund
    PEAK_HOLD = 0.35       # sekund ein topp blir ståande før han dett
    PEAK_GRAVITY = 3.0     # akselerasjon for fallande toppar

    def __init__(self, source=None, **kwargs):
        super().__init__(**kwargs)
        self.source = source or (lambda bands: None)
        self._levels = np.zeros(0)
        self._peaks = np.zeros(0)
        self._peak_age = np.zeros(0)
        self._peak_speed = np.zeros(0)
        self._last_frame = time.monotonic()
        self._row_styles = []

    def on_mount(self):
        self.set_interval(1 / self.FPS, self._next_frame)

    def on_resize(self):
        bands = max(self.size.width // (self.BAR_WIDTH + self.GAP), 1)
        if bands != len(self._levels):
            self._levels = np.zeros(bands)
            self._peaks = np.zeros(bands)
            self._peak_age = np.zeros(bands)
            self._peak_speed = np.zeros(bands)
        height = max(self.size.height, 1)
        self._row_styles = [
            Style(color=_gradient_color((height - 1 - y) / max(height - 1, 1))) for y in range(height)
        ]

    # --- Animasjon -----------------------------------------------------

    def _next_frame(self):
        now = time.monotonic()
        dt = min(now - self._last_frame, 0.1)
        self._last_frame = now
        if not self.display or not len(self._levels):
            return

        target = self.source(len(self._levels))
        if target is None:
            target = np.zeros(len(self._levels))

        # Søylene stig med ein gong, men fell mjukt
        self._levels = np.maximum(target, self._levels - self.FALL_SPEED * dt)

        # Toppane blir ståande litt, og fell så med aukande fart
        risen = self._levels >= self._peaks
        self._peaks[risen] = self._levels[risen]
        self._peak_age[risen] = 0
        self._peak_speed[risen] = 0
        falling = ~risen
        self._peak_age[falling] += dt
        dropping = falling & (self._peak_age > self.PEAK_HOLD)
        self._peak_speed[dropping] += self.PEAK_GRAVITY * dt
        self._peaks[dropping] = np.maximum(self._peaks[dropping] - self._peak_speed[dropping] * dt, self._levels[dropping])

        if self._peaks.any() or target.any():
            self.refresh()

    # --- Teikning ------------------------------------------------------

    def render_line(self, y):
        height = self.size.height
        if not self._row_styles or y >= len(self._row_styles):
            return Strip.blank(self.size.width)

        row_from_bottom = height - 1 - y
        base = self.rich_style  # bakgrunnen frå CSS/temaet
        style = base + self._row_styles[y]
        peak_style = base + Style(color="grey85")
        gap = " " * self.GAP
        segments = []
        for level, peak in zip(self._levels, self._peaks):
            # Kor mange åttendedelar av denne ruta søyla fyller
            eighths = int(round(level * height * 8)) - row_from_bottom * 8
            peak_row = min(int(peak * height), height - 1)
            if eighths >= 8:
                char, cell_style = BLOCKS[8], style
            elif eighths > 0:
                char, cell_style = BLOCKS[eighths], style
            elif peak > 0.02 and peak_row == row_from_bottom:
                char, cell_style = PEAK, peak_style
            else:
                char, cell_style = " ", base
            segments.append(Segment(char * self.BAR_WIDTH, cell_style))
            segments.append(Segment(gap, base))
        return Strip(segments).crop(0, self.size.width).extend_cell_length(self.size.width, base)
