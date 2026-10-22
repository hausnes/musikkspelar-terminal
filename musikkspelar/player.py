from enum import Enum, auto

from .models import PlayQueue


class PlayerState(Enum):
    STOPPED = auto()
    PLAYING = auto()
    PAUSED = auto()


class Player:
    """A class to control playback: connects the play queue to an audio backend.

    The Player knows nothing about the user interface. Anyone who wants to
    know when something changes can register a listener with add_listener().

    The backend may report events from its own thread. dispatch is used to
    move them over to the thread the Player lives in (the UI thread)."""

    RESTART_THRESHOLD = 3  # sekund: «førre» startar låta på nytt etter så lang tid

    def __init__(self, backend, dispatch=None):
        self.queue = PlayQueue()
        self.state = PlayerState.STOPPED
        self._backend = backend
        self._listeners = []
        dispatch = dispatch or (lambda callback: callback())
        backend.on_track_started_automatically = lambda: dispatch(self._on_automatic_next)
        backend.on_playback_finished = lambda: dispatch(self._on_finished)

    # --- Lyttarar (observer-mønsteret) ---------------------------------

    def add_listener(self, callback):
        """callback() is called every time the state, track or queue changes."""
        self._listeners.append(callback)

    def _notify(self):
        for callback in self._listeners:
            callback()

    # --- Avspeling ------------------------------------------------------

    @property
    def current_track(self):
        return self.queue.current if self.state is not PlayerState.STOPPED else None

    def play_tracks(self, tracks, start_index=0):
        """Replaces the queue with tracks and starts playing at start_index."""
        self.queue.replace(tracks, start_index)
        self._play_current()

    def play_queue_index(self, index):
        """Plays the track at index in the queue."""
        self.queue.jump_to(index)
        self._play_current()

    def _play_current(self):
        track = self.queue.current
        if track is None:
            self.stop()
            return
        self._backend.play(track.path)
        self.state = PlayerState.PLAYING
        self._preload_next()
        self._notify()

    def _preload_next(self):
        """Tells the backend which file comes next, so the transition is gapless."""
        if self.state is PlayerState.STOPPED:
            return
        upcoming = self.queue.peek_next(automatic=True)
        self._backend.set_next(upcoming.path if upcoming else None)

    def toggle_pause(self):
        if self.state is PlayerState.PLAYING:
            self._backend.paused = True
            self.state = PlayerState.PAUSED
        elif self.state is PlayerState.PAUSED:
            self._backend.paused = False
            self.state = PlayerState.PLAYING
        elif len(self.queue):
            # Stoppa: start frå gjeldande (eller første) låt i køen
            if self.queue.current is None:
                self.queue.rewind()
            self._play_current()
            return
        self._notify()

    def stop(self):
        self.state = PlayerState.STOPPED
        self._backend.stop()
        self._notify()

    def next(self):
        if self.queue.advance(automatic=False) is not None:
            self._play_current()

    def previous(self):
        """Restarts the track if it has played a while, otherwise goes to the previous one."""
        position = self._backend.position or 0
        if position > self.RESTART_THRESHOLD or self.queue.go_back() is None:
            self.seek(0, absolute=True)
        else:
            self._play_current()

    def seek(self, seconds, absolute=False):
        self._backend.seek(seconds, absolute)

    @property
    def position(self):
        return self._backend.position

    @property
    def duration(self):
        duration = self._backend.duration
        if duration is None and self.current_track is not None:
            return self.current_track.duration
        return duration

    @property
    def volume(self):
        return self._backend.volume

    @volume.setter
    def volume(self, value):
        self._backend.volume = value
        self._notify()

    # --- Kø og modusar -------------------------------------------------

    def enqueue(self, tracks):
        self.queue.add(tracks)
        self._preload_next()
        self._notify()

    def remove_from_queue(self, index):
        was_current = index == self.queue.current_index
        self.queue.remove(index)
        if was_current and self.state is not PlayerState.STOPPED:
            self._play_current()
        else:
            self._preload_next()
            self._notify()

    def clear_queue(self):
        self.queue.clear()
        self.stop()

    def toggle_shuffle(self):
        self.queue.toggle_shuffle()
        self._preload_next()
        self._notify()

    def cycle_repeat(self):
        self.queue.cycle_repeat()
        self._preload_next()
        self._notify()

    # --- Hendingar frå backend ----------------------------------------

    def _on_automatic_next(self):
        """The backend moved on to the preloaded track by itself."""
        self.queue.advance(automatic=True)
        self._preload_next()
        self._notify()

    def _on_finished(self):
        """There was nothing more to play."""
        if self.state is not PlayerState.STOPPED:
            self.state = PlayerState.STOPPED
            self.queue.rewind()  # neste trykk på play startar køen frå byrjinga
            self._notify()

    def close(self):
        self._backend.close()
