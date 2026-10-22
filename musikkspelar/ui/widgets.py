from rich.text import Text
from textual.binding import Binding
from textual.content import Content
from textual.message import Message
from textual.widget import Widget
from textual.widgets import DataTable, Static, Tree

from ..models import RepeatMode, Track, format_time
from ..player import PlayerState


class LibraryTree(Tree):
    """Shows the library as Artist → Album → Track."""

    BINDINGS = [Binding("a", "enqueue", "Legg i kø")]

    class PlayRequested(Message):
        def __init__(self, tracks, start_index):
            super().__init__()
            self.tracks = tracks
            self.start_index = start_index

    class EnqueueRequested(Message):
        def __init__(self, tracks):
            super().__init__()
            self.tracks = tracks

    def __init__(self, **kwargs):
        super().__init__("Bibliotek", **kwargs)
        self.show_root = False
        self.library = None
        self.border_title = "Bibliotek"

    def load(self, library):
        """Fills the tree from a Library."""
        self.library = library
        self.clear()
        for artist in library.artists:
            artist_node = self.root.add(artist, data=("artist", artist))
            for album in library.albums_by(artist):
                tracks = library.tracks_in(artist, album)
                year = f" ({tracks[0].year})" if tracks[0].year else ""
                album_node = artist_node.add(f"{album}{year}", data=("album", artist, album))
                for track in tracks:
                    number = f"{track.track_number:>2}. " if track.track_number else ""
                    album_node.add_leaf(f"{number}{track.title}", data=track)
        self.border_subtitle = f"{len(library)} låtar"
        self.cursor_line = 0  # elles står markøren ingen stad, og første Enter gjer ingenting

    def _tracks_for(self, node):
        """Returns the tracks a node represents (one track, an album or an artist)."""
        data = node.data
        if isinstance(data, Track):
            return [data]
        if data and data[0] == "album":
            return self.library.tracks_in(data[1], data[2])
        if data and data[0] == "artist":
            return self.library.tracks_by(data[1])
        return []

    def on_tree_node_selected(self, event):
        # Enter på ei låt: spel albumet frå denne låta. Enter på artist/album opnar/lukkar.
        if isinstance(event.node.data, Track):
            album_tracks = self._tracks_for(event.node.parent)
            self.post_message(self.PlayRequested(album_tracks, album_tracks.index(event.node.data)))

    def action_enqueue(self):
        if self.cursor_node is not None:
            tracks = self._tracks_for(self.cursor_node)
            if tracks:
                self.post_message(self.EnqueueRequested(tracks))


class QueueView(DataTable):
    """Shows the play queue. The current track is marked with ▶."""

    BINDINGS = [
        Binding("x,delete", "remove", "Fjern"),
    ]

    class PlayIndexRequested(Message):
        def __init__(self, index):
            super().__init__()
            self.index = index

    class RemoveRequested(Message):
        def __init__(self, index):
            super().__init__()
            self.index = index

    def __init__(self, **kwargs):
        super().__init__(cursor_type="row", zebra_stripes=True, **kwargs)
        self.border_title = "Kø"

    def on_mount(self):
        self.add_column("", key="mark", width=2)
        self.add_column("Tittel", key="title")
        self.add_column("Artist", key="artist")
        self.add_column("Album", key="album")
        self.add_column("Tid", key="time")

    def show(self, queue, playing_index):
        """Redraws the table from a PlayQueue, keeping the cursor in place."""
        cursor = self.cursor_row
        self.clear()
        for index, track in enumerate(queue.tracks):
            current = index == playing_index
            self.add_row(
                Text("▶", style="bold") if current else "",
                Text(track.title, style="bold" if current else ""),
                track.artist,
                track.album,
                Text(format_time(track.duration), justify="right"),
                key=str(index),
            )
        if self.row_count:
            self.move_cursor(row=min(cursor, self.row_count - 1))
        mode = " · ".join(filter(None, [
            "⇄ stokka" if queue.shuffle else "",
            f"↻ {queue.repeat.value}" if queue.repeat is not RepeatMode.OFF else "",
        ]))
        total = sum(track.duration for track in queue.tracks)
        self.border_subtitle = f"{len(queue)} låtar · {format_time(total)}" + (f" · {mode}" if mode else "")

    def on_data_table_row_selected(self, event):
        self.post_message(self.PlayIndexRequested(event.cursor_row))

    def action_remove(self):
        if self.row_count:
            self.post_message(self.RemoveRequested(self.cursor_row))


class ProgressLine(Widget):
    """A progress bar with elapsed and total time. Click on it to seek."""

    DEFAULT_CSS = """
    ProgressLine { height: 1; }
    """

    class SeekRequested(Message):
        def __init__(self, fraction):
            super().__init__()
            self.fraction = fraction

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.position = 0.0
        self.duration = 0.0

    def update_time(self, position, duration):
        if (position, duration) != (self.position, self.duration):
            self.position, self.duration = position or 0.0, duration or 0.0
            self.refresh()

    def _bar_area(self):
        """Returns (start column, width) of the bar itself."""
        left = len(format_time(self.position)) + 1
        right = len(format_time(self.duration)) + 1
        return left, max(self.size.width - left - right, 0)

    def render(self):
        start, width = self._bar_area()
        fraction = min(self.position / self.duration, 1.0) if self.duration else 0.0
        filled = int(fraction * width)
        return Content.assemble(
            (format_time(self.position) + " ", "bold"),
            ("━" * filled, "$accent"),
            ("─" * (width - filled), "$foreground 20%"),
            (" " + format_time(self.duration), "dim"),
        )

    def on_click(self, event):
        start, width = self._bar_area()
        if width and self.duration:
            fraction = (event.x - start) / width
            self.post_message(self.SeekRequested(min(max(fraction, 0.0), 1.0)))


class NowPlaying(Widget):
    """Shows the current track, progress and the player's modes."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.border_title = "No spelar"

    def compose(self):
        yield Static(id="np-title")
        yield Static(id="np-details")
        yield ProgressLine(id="np-progress")
        yield Static(id="np-status")

    def show(self, player):
        track = player.current_track
        icon = {PlayerState.PLAYING: "▶", PlayerState.PAUSED: "⏸", PlayerState.STOPPED: "■"}[player.state]
        if track is None:
            self.query_one("#np-title", Static).update(Content.styled(f"{icon}  Ingenting spelar", "dim"))
            self.query_one("#np-details", Static).update("   Vel ei låt i biblioteket og trykk Enter")
        else:
            self.query_one("#np-title", Static).update(Content.styled(f"{icon}  {track.title}", "bold $text"))
            year = f" ({track.year})" if track.year else ""
            self.query_one("#np-details", Static).update(Content(f"   {track.artist} — {track.album}{year}"))

        queue = player.queue
        repeating = queue.repeat is not RepeatMode.OFF
        status = Content.assemble(
            "   ",
            ("⇄ Stokk", "bold $accent" if queue.shuffle else "dim"),
            "   ",
            (f"↻ Gjenta: {queue.repeat.value}", "bold $accent" if repeating else "dim"),
            f"   Volum {player.volume} %",
        )
        self.query_one("#np-status", Static).update(status)
        self.update_time(player)

    def update_time(self, player):
        if player.current_track is None:
            self.query_one(ProgressLine).update_time(0, 0)
        else:
            self.query_one(ProgressLine).update_time(player.position, player.duration)
