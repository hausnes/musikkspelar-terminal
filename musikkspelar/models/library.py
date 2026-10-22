from collections import defaultdict
from pathlib import Path

from .track import SUPPORTED_EXTENSIONS, Track


class Library:
    """A class to represent all the music in a folder, grouped by artist and album."""

    def __init__(self, root, extensions=SUPPORTED_EXTENSIONS):
        self.root = Path(root).expanduser().resolve()
        self.extensions = extensions
        self._albums = defaultdict(lambda: defaultdict(list))  # artist -> album -> [Track]
        self.errors = []  # filer som ikkje kunne lesast

    def scan(self):
        """Finds and reads all supported audio files under root (recursively)."""
        self._albums.clear()
        self.errors.clear()
        for path in sorted(self.root.rglob("*")):
            if path.suffix.lower() not in self.extensions or path.name.startswith("."):
                continue
            try:
                track = Track.from_file(path, self.root)
            except Exception as error:  # øydelagde filer skal ikkje stoppe skanninga
                self.errors.append((path, error))
                continue
            self._albums[track.album_artist][track.album].append(track)

        for albums in self._albums.values():
            for tracks in albums.values():
                tracks.sort(key=lambda t: t.sort_key)

    @property
    def artists(self):
        """Returns all artists, sorted alphabetically."""
        return sorted(self._albums, key=str.lower)

    def albums_by(self, artist):
        """Returns the album names for an artist, sorted by year and then name."""
        albums = self._albums.get(artist, {})
        return sorted(albums, key=lambda album: (albums[album][0].year or "", album.lower()))

    def tracks_in(self, artist, album):
        """Returns the tracks in an album, in track order."""
        return list(self._albums.get(artist, {}).get(album, []))

    def tracks_by(self, artist):
        """Returns all tracks by an artist, album by album."""
        return [track for album in self.albums_by(artist) for track in self.tracks_in(artist, album)]

    @property
    def all_tracks(self):
        return [track for artist in self.artists for track in self.tracks_by(artist)]

    def __len__(self):
        return sum(len(tracks) for albums in self._albums.values() for tracks in albums.values())
