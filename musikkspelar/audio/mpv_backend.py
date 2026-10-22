import os
import sys

from .backend import AudioBackend

# python-mpv brukar ctypes.util.find_library, som ikkje ser i Homebrew-mappene
# av seg sjølv (særleg /opt/homebrew/lib på Apple Silicon).
if sys.platform == "darwin" and "DYLD_FALLBACK_LIBRARY_PATH" not in os.environ:
    os.environ["DYLD_FALLBACK_LIBRARY_PATH"] = "/opt/homebrew/lib:/usr/local/lib:/usr/lib"

import mpv  # noqa: E402  (må importerast etter at stien over er sett)


class MpvBackend(AudioBackend):
    """Plays audio with libmpv.

    mpv keeps its own little playlist: [current file, next file]. When the
    current file ends, mpv moves straight on to the next one without a gap,
    and we are told about it through the 'start-file' event."""

    def __init__(self):
        super().__init__()
        self._mpv = mpv.MPV(
            video=False,
            vid=False,
            ytdl=False,
            gapless_audio="weak",
            # CoreAudio på macOS nektar å opne mono-lyd frå libmpv, og reserveløysinga
            # (AVFoundation) hoppar til slutten av fila ved spoling. Stereo fungerer.
            audio_channels="stereo",
            audio_display=False,
            input_default_bindings=False,
            input_terminal=False,  # Textual eig terminalen, ikkje mpv
            terminal=False,
        )
        self._mpv.event_callback("start-file")(self._handle_start_file)
        self._mpv.observe_property("idle-active", self._handle_idle)

    # --- Hendingar frå mpv (køyrer i mpv sin tråd) ----------------------

    def _handle_start_file(self, event):
        # play() byrjar alltid på posisjon 0. Står vi lenger ut i lista,
        # har mpv gått vidare av seg sjølv.
        if (self._mpv.playlist_pos or 0) > 0:
            self._mpv.command("playlist-remove", 0)
            self.on_track_started_automatically()

    def _handle_idle(self, _name, idle):
        if idle:
            self.on_playback_finished()

    # --- AudioBackend --------------------------------------------------

    def play(self, path):
        self._mpv.loadfile(str(path), "replace")
        self._mpv.pause = False

    def set_next(self, path):
        self._mpv.command("playlist-clear")  # fjernar alt bortsett frå gjeldande fil
        if path is not None:
            self._mpv.loadfile(str(path), "append")

    def stop(self):
        self._mpv.command("stop")

    @property
    def paused(self):
        return bool(self._mpv.pause)

    @paused.setter
    def paused(self, value):
        self._mpv.pause = value

    @property
    def volume(self):
        return round(self._mpv.volume)

    @volume.setter
    def volume(self, value):
        self._mpv.volume = max(0, min(100, value))

    @property
    def position(self):
        return self._mpv.time_pos

    @property
    def duration(self):
        return self._mpv.duration

    def seek(self, seconds, absolute=False):
        if self._mpv.time_pos is None:
            return
        try:
            self._mpv.seek(seconds, "absolute" if absolute else "relative", "exact")
        except SystemError:
            pass  # mpv avviser spoling medan fila framleis lastar

    def close(self):
        self._mpv.terminate()
