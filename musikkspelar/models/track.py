import re
from dataclasses import dataclass
from pathlib import Path

import mutagen

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".ogg", ".opus", ".m4a", ".wav"}

UNKNOWN_ARTIST = "Ukjend artist"
UNKNOWN_ALBUM = "Ukjend album"


def _first(tags, key):
    """Returns the first value of a tag, or None if it is missing or empty."""
    values = tags.get(key) if tags else None
    if not values:
        return None
    value = str(values[0]).strip()
    return value or None


def _parse_number(text):
    """Parses tag numbers like '3' or '3/12'. Returns None if not a number."""
    if not text:
        return None
    try:
        return int(text.split("/")[0])
    except ValueError:
        return None


def _number_from_filename(path):
    """Guesses the track number from file names like '03 - Song.mp3'."""
    match = re.match(r"\s*(\d{1,3})(?!\d)", path.stem)
    return int(match.group(1)) if match else None


@dataclass(frozen=True)
class Track:
    """A class to represent a track (a song or sound file)."""

    path: Path
    title: str
    artist: str
    album: str
    album_artist: str
    track_number: int | None = None
    disc_number: int | None = None
    year: str | None = None
    duration: float = 0.0  # sekund

    @classmethod
    def from_file(cls, path, root=None):
        """Creates a Track by reading the tags in the file.

        Missing tags are guessed from the folder structure
        (root/Artist/Album/file.mp3)."""
        path = Path(path)
        audio = mutagen.File(path, easy=True)
        tags = audio.tags if audio is not None else None

        # Reserveverdiar frå mappestrukturen dersom taggane manglar
        folders = path.relative_to(root).parts[:-1] if root else path.parts[:-1]
        folder_album = folders[-1] if len(folders) >= 1 else None
        folder_artist = folders[-2] if len(folders) >= 2 else None

        artist = _first(tags, "artist") or folder_artist or UNKNOWN_ARTIST
        return cls(
            path=path,
            title=_first(tags, "title") or path.stem,
            artist=artist,
            album=_first(tags, "album") or folder_album or UNKNOWN_ALBUM,
            album_artist=_first(tags, "albumartist") or artist,
            track_number=_parse_number(_first(tags, "tracknumber")) or _number_from_filename(path),
            disc_number=_parse_number(_first(tags, "discnumber")),
            year=(_first(tags, "date") or "")[:4] or None,
            duration=audio.info.length if audio is not None else 0.0,
        )

    @property
    def sort_key(self):
        """Key for sorting tracks within an album."""
        return (self.disc_number or 0, self.track_number or 0, self.title.lower())


def format_time(seconds):
    """Formats seconds as m:ss (or h:mm:ss)."""
    seconds = int(seconds or 0)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}:{minutes:02}:{secs:02}"
    return f"{minutes}:{secs:02}"
