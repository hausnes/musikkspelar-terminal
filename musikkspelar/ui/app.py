from textual import work
from textual.app import App
from textual.binding import Binding
from textual.containers import Horizontal
from textual.message import Message
from textual.widgets import Footer, Header

from ..audio.mpv_backend import MpvBackend
from ..models import Library
from ..player import Player
from .widgets import LibraryTree, NowPlaying, QueueView

SEEK_STEP = 5      # sekund
VOLUME_STEP = 5    # prosent


class BackendEvent(Message):
    """Carries a callback from the audio thread over to the UI thread."""

    def __init__(self, callback):
        super().__init__()
        self.callback = callback


class MusicPlayerApp(App):
    """The terminal music player."""

    CSS_PATH = "app.tcss"
    TITLE = "Musikkspelar"

    BINDINGS = [
        # priority=True: tastane skal verke same kva panel som har fokus
        Binding("space", "toggle_pause", "Play/pause", priority=True),
        Binding("n", "next", "Neste", priority=True),
        Binding("p", "previous", "Førre", priority=True),
        Binding("left", "seek(-1)", "Spol -5s", show=False, priority=True),
        Binding("right", "seek(1)", "Spol +5s", show=False, priority=True),
        Binding("plus,equals_sign", "volume(1)", "Volum +", show=False),
        Binding("minus", "volume(-1)", "Volum -", show=False),
        Binding("s", "shuffle", "Stokk"),
        Binding("r", "repeat", "Gjenta"),
        Binding("c", "clear_queue", "Tøm kø"),
        Binding("q", "quit", "Avslutt"),
    ]

    def __init__(self, music_folder):
        super().__init__()
        self.library = Library(music_folder)
        # Hendingar frå mpv kjem i ein annan tråd. post_message er trådtrygg
        # og blokkerer ikkje, så vi sender dei vidare som meldingar.
        self.player = Player(MpvBackend(), dispatch=lambda callback: self.post_message(BackendEvent(callback)))
        self.player.add_listener(self.refresh_views)

    def compose(self):
        yield Header(show_clock=True)
        with Horizontal(id="main"):
            yield LibraryTree(id="library")
            yield QueueView(id="queue")
        yield NowPlaying(id="now-playing")
        yield Footer()

    def on_mount(self):
        self.sub_title = f"Skannar {self.library.root} …"
        self.player.volume = 80
        self.set_interval(0.25, self._tick)
        self.scan_library()

    def on_unmount(self):
        self.player.close()

    @work(thread=True, exclusive=True)
    def scan_library(self):
        self.library.scan()
        self.call_from_thread(self._library_loaded)

    def _library_loaded(self):
        tree = self.query_one(LibraryTree)
        tree.load(self.library)
        tree.focus()
        self.sub_title = str(self.library.root)
        if self.library.errors:
            self.notify(f"{len(self.library.errors)} filer kunne ikkje lesast", severity="warning")
        if not len(self.library):
            self.notify("Fann ingen musikkfiler i mappa", severity="error", timeout=10)

    # --- Oppdatering av visninga --------------------------------------

    def refresh_views(self):
        self.query_one(NowPlaying).show(self.player)
        playing = self.player.queue.current_index if self.player.current_track else None
        self.query_one(QueueView).show(self.player.queue, playing)

    def _tick(self):
        self.query_one(NowPlaying).update_time(self.player)

    # --- Meldingar frå widgets og lydmotoren --------------------------

    def on_backend_event(self, message):
        message.callback()

    def on_library_tree_play_requested(self, message):
        self.player.play_tracks(message.tracks, message.start_index)

    def on_library_tree_enqueue_requested(self, message):
        self.player.enqueue(message.tracks)
        self.notify(f"La til {len(message.tracks)} låt(ar) i køen", timeout=2)

    def on_queue_view_play_index_requested(self, message):
        self.player.play_queue_index(message.index)

    def on_queue_view_remove_requested(self, message):
        self.player.remove_from_queue(message.index)

    def on_progress_line_seek_requested(self, message):
        if self.player.duration:
            self.player.seek(message.fraction * self.player.duration, absolute=True)

    # --- Handlingar (tastatur) -----------------------------------------

    def action_toggle_pause(self):
        self.player.toggle_pause()

    def action_next(self):
        self.player.next()

    def action_previous(self):
        self.player.previous()

    def action_seek(self, direction):
        self.player.seek(direction * SEEK_STEP)
        self._tick()

    def action_volume(self, direction):
        self.player.volume = self.player.volume + direction * VOLUME_STEP

    def action_shuffle(self):
        self.player.toggle_shuffle()

    def action_repeat(self):
        self.player.cycle_repeat()

    def action_clear_queue(self):
        self.player.clear_queue()
