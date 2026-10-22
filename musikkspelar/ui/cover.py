from io import BytesIO

from PIL import Image, UnidentifiedImageError
from rich.color import Color
from rich.segment import Segment
from rich.style import Style
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Static

HALF_BLOCK = "▀"  # øvre halvdel = forgrunnsfarge, nedre halvdel = bakgrunnsfarge
PLACEHOLDER_COLORS = ((48, 48, 58), (36, 36, 44))


class CoverView(Widget):
    """Shows an album cover using half blocks: every cell is two pixels tall.

    Covers are square, and a terminal cell is about twice as tall as it is
    wide, so a cover of N cells width and N/2 rows comes out square."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._image = None
        self._lines = []
        self._rendered_size = None

    def set_image(self, data):
        """Shows the image in data (bytes), or a placeholder if data is None."""
        image = None
        if data:
            try:
                image = Image.open(BytesIO(data))
                image.draft("RGB", (400, 400))  # lar JPEG dekode i lågare oppløysing, mykje raskare
                image = image.convert("RGB")
            except (UnidentifiedImageError, OSError):
                image = None
        self._image = image
        self._rendered_size = None
        self.refresh()

    def _render_lines(self):
        """Scales the image to fit the widget and converts it to strips."""
        width, height = self.size
        side = min(width, height * 2)  # i pikslar
        if side <= 0:
            return []
        if self._image is None:
            image = self._placeholder(side)
        else:
            image = self._image.resize((side, side), Image.Resampling.LANCZOS)
        pixels = image.load()

        base = self.rich_style
        left_pad = (width - side) // 2
        top_pad = (height - (side + 1) // 2) // 2
        blank = Strip.blank(width, base)
        lines = [blank] * top_pad
        for row in range(0, side, 2):
            segments = [Segment(" " * left_pad, base)]
            for x in range(side):
                top = pixels[x, row]
                bottom = pixels[x, row + 1] if row + 1 < side else None
                style = Style(
                    color=Color.from_rgb(*top),
                    bgcolor=Color.from_rgb(*bottom) if bottom else base.bgcolor,
                )
                segments.append(Segment(HALF_BLOCK, style))
            lines.append(Strip(segments).extend_cell_length(width, base))
        lines += [blank] * (height - len(lines))
        return lines

    @staticmethod
    def _placeholder(side):
        """A dim square with a music note, for tracks without a cover."""
        image = Image.new("RGB", (side, side), PLACEHOLDER_COLORS[0])
        pixels = image.load()
        light = (110, 110, 130)
        # Ein enkel note: eit hovud og ein stilk, skalert etter storleiken
        cx, cy, r = side * 0.42, side * 0.68, max(side * 0.11, 1)
        stem_x = int(cx + r * 0.8)
        for y in range(side):
            for x in range(side):
                if ((x - cx) / 1.25) ** 2 + (y - cy) ** 2 <= r * r:
                    pixels[x, y] = light
                elif stem_x <= x <= stem_x + max(side // 16, 0) and side * 0.25 <= y <= cy:
                    pixels[x, y] = light
                elif x < 1 or y < 1 or x >= side - 1 or y >= side - 1:
                    pixels[x, y] = PLACEHOLDER_COLORS[1]
        return image

    def render_line(self, y):
        if self._rendered_size != self.size:
            self._lines = self._render_lines()
            self._rendered_size = self.size
        if y < len(self._lines):
            return self._lines[y]
        return Strip.blank(self.size.width, self.rich_style)


class CoverScreen(ModalScreen):
    """Shows the cover large, on top of everything else."""

    BINDINGS = [Binding("escape,i,q,enter,space", "dismiss", "Lukk")]

    DEFAULT_CSS = """
    CoverScreen {
        align: center middle;
        background: $background 70%;
    }
    #cover-box {
        width: auto;
        height: 90%;
        border: round $accent;
        border-title-color: $accent;
        border-title-style: bold;
        background: $surface;
        padding: 0 1;
    }
    #cover-big {
        width: 80;
        height: 1fr;
    }
    #cover-caption {
        width: 80;
        content-align: center middle;
        color: $text-muted;
    }
    """

    def __init__(self, data, title, caption):
        super().__init__()
        self._data = data
        self._title = title
        self._caption = caption

    def compose(self):
        with Vertical(id="cover-box"):
            yield CoverView(id="cover-big")
            yield Static(self._caption, id="cover-caption")

    def on_mount(self):
        self.query_one("#cover-box").border_title = self._title
        self.query_one(CoverView).set_image(self._data)
        self._fit_to_screen()

    def on_resize(self):
        self._fit_to_screen()

    def _fit_to_screen(self):
        # Kvadratisk: breidda i ruter = høgda i ruter × 2 (minus ramme og bilettekst)
        rows = int(self.size.height * 0.9) - 3
        width = max(min(rows * 2, self.size.width - 6), 10)
        self.query_one("#cover-big").styles.width = width
        self.query_one("#cover-caption").styles.width = width

    def on_click(self):
        self.dismiss()
