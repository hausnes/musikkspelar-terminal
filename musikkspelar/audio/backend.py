from abc import ABC, abstractmethod

from ..models.track import SUPPORTED_EXTENSIONS


class AudioBackend(ABC):
    """The interface every audio engine must implement.

    The Player only talks to this class, so the engine (mpv or miniaudio)
    can be replaced without touching the rest of the program.

    Callbacks may be called from another thread than the one that created
    the backend:
      on_track_started_automatically(): playback moved on to the preloaded
          next file by itself (gapless).
      on_playback_finished(): there was nothing more to play.
    """

    # Filtypane backenden kan spele. Biblioteket hoppar over alle andre.
    SUPPORTED_EXTENSIONS = SUPPORTED_EXTENSIONS

    def __init__(self):
        self.on_track_started_automatically = lambda: None
        self.on_playback_finished = lambda: None

    @abstractmethod
    def play(self, path):
        """Starts playing the file at path right away."""

    @abstractmethod
    def set_next(self, path):
        """Preloads the file that should follow the current one (None = nothing)."""

    @abstractmethod
    def stop(self):
        """Stops playback and forgets the current and next file."""

    @property
    @abstractmethod
    def paused(self):
        """True if playback is paused."""

    @paused.setter
    @abstractmethod
    def paused(self, value):
        pass

    @property
    @abstractmethod
    def volume(self):
        """Volume from 0 to 100."""

    @volume.setter
    @abstractmethod
    def volume(self, value):
        pass

    @property
    @abstractmethod
    def position(self):
        """Seconds played of the current file, or None if nothing is loaded."""

    @property
    @abstractmethod
    def duration(self):
        """Length of the current file in seconds, or None if unknown."""

    @abstractmethod
    def seek(self, seconds, absolute=False):
        """Seeks seconds forwards/backwards, or to seconds if absolute is True."""

    def close(self):
        """Releases the resources used by the backend."""
