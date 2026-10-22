import random
from enum import Enum


class RepeatMode(Enum):
    OFF = "av"
    ALL = "alle"
    ONE = "éin"

    def next(self):
        modes = list(RepeatMode)
        return modes[(modes.index(self) + 1) % len(modes)]


class PlayQueue:
    """A class to represent the play queue, with shuffle and repeat.

    The tracks are always kept in the order they were added. When shuffle is
    on, a separate play order (a list of indexes) decides what comes next."""

    def __init__(self):
        self.tracks = []
        self._order = []        # indeksar i self.tracks, i den rekkjefølgja dei skal spelast
        self._position = None   # kvar i self._order vi er, eller None
        self.shuffle = False
        self.repeat = RepeatMode.OFF

    # --- Innhald -------------------------------------------------------

    def replace(self, tracks, start_index=0):
        """Replaces the whole queue and sets the current track to start_index."""
        self.tracks = list(tracks)
        self._order = list(range(len(self.tracks)))
        self._position = start_index if self.tracks else None
        if self.shuffle:
            self._shuffle_order()

    def add(self, tracks):
        """Adds tracks to the end of the queue."""
        first_new = len(self.tracks)
        self.tracks.extend(tracks)
        new_indexes = list(range(first_new, len(self.tracks)))
        if self.shuffle:
            random.shuffle(new_indexes)
        self._order.extend(new_indexes)

    def remove(self, index):
        """Removes the track at index (in self.tracks)."""
        if not 0 <= index < len(self.tracks):
            return
        current = self.current_index
        del self.tracks[index]
        self._order = [i - (i > index) for i in self._order if i != index]
        if current is None or not self.tracks:
            self._position = None
        elif current == index:
            # Den gjeldande låta forsvann: neste låt tek over plassen
            self._position = min(self._position, len(self._order) - 1)
        else:
            self._position = self._order.index(current - (current > index))

    def clear(self):
        self.tracks = []
        self._order = []
        self._position = None

    def __len__(self):
        return len(self.tracks)

    # --- Gjeldande låt -------------------------------------------------

    @property
    def current_index(self):
        """Index (in self.tracks) of the current track, or None."""
        if self._position is None:
            return None
        return self._order[self._position]

    @property
    def current(self):
        index = self.current_index
        return None if index is None else self.tracks[index]

    def jump_to(self, index):
        """Makes the track at index (in self.tracks) the current one."""
        if 0 <= index < len(self.tracks):
            self._position = self._order.index(index)

    def rewind(self):
        """Goes back to the first track in the play order."""
        self._position = 0 if self._order else None

    # --- Navigering ----------------------------------------------------

    def _next_position(self, automatic):
        """Finds the next position in the play order, or None at the end.

        automatic is True when the previous track finished by itself, which
        is the only time 'repeat one' should repeat."""
        if not self._order:
            return None
        if self._position is None:
            return 0
        if automatic and self.repeat is RepeatMode.ONE:
            return self._position
        if self._position + 1 < len(self._order):
            return self._position + 1
        if self.repeat is not RepeatMode.OFF:
            return 0
        return None

    def peek_next(self, automatic=True):
        """Returns the track that comes next, without moving there."""
        position = self._next_position(automatic)
        return None if position is None else self.tracks[self._order[position]]

    def advance(self, automatic=False):
        """Moves to the next track and returns it, or None at the end of the queue."""
        position = self._next_position(automatic)
        if position is not None:
            self._position = position
        return None if position is None else self.current

    def go_back(self):
        """Moves to the previous track and returns it."""
        if not self._order:
            return None
        if self._position is None or self._position > 0:
            self._position = max((self._position or 0) - 1, 0)
        elif self.repeat is not RepeatMode.OFF:
            self._position = len(self._order) - 1
        return self.current

    # --- Modusar -------------------------------------------------------

    def toggle_shuffle(self):
        self.shuffle = not self.shuffle
        if self.shuffle:
            self._shuffle_order()
        else:
            current = self.current_index
            self._order = list(range(len(self.tracks)))
            self._position = current

    def cycle_repeat(self):
        self.repeat = self.repeat.next()

    def _shuffle_order(self):
        """Shuffles the play order, but keeps the current track first."""
        current = self.current_index
        rest = [i for i in range(len(self.tracks)) if i != current]
        random.shuffle(rest)
        if current is None:
            self._order = rest
        else:
            self._order = [current] + rest
            self._position = 0
