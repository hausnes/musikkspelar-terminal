import base64
from functools import lru_cache

import mutagen
from mutagen.flac import Picture
from mutagen.id3 import ID3
from mutagen.mp4 import MP4Tags

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"}
FOLDER_NAMES = ("cover", "folder", "front", "album", "albumart")
FRONT_COVER = 3  # bilettype for framside i ID3 og FLAC


def _prefer_front(pictures):
    """Returns the data of the front cover, or of the first picture if there is none."""
    pictures = list(pictures)
    if not pictures:
        return None
    front = next((p for p in pictures if p.type == FRONT_COVER), pictures[0])
    return front.data


def _embedded_cover(path):
    """Reads a cover image stored inside the audio file's tags."""
    try:
        audio = mutagen.File(path)
    except mutagen.MutagenError:
        return None  # fila kan ikkje lesast, men mappa kan framleis ha eit cover
    if audio is None:
        return None
    if getattr(audio, "pictures", None):  # FLAC
        return _prefer_front(audio.pictures)
    tags = audio.tags
    if tags is None:
        return None
    if isinstance(tags, ID3):  # MP3
        return _prefer_front(tags.getall("APIC"))
    if isinstance(tags, MP4Tags):  # M4A
        covers = tags.get("covr")
        return bytes(covers[0]) if covers else None
    blocks = tags.get("metadata_block_picture")  # OGG og Opus
    if blocks:
        return _prefer_front(Picture(base64.b64decode(block)) for block in blocks)
    return None


def _folder_cover(folder):
    """Finds a cover image in the album folder, e.g. cover.jpg or folder.png."""
    images = sorted(
        (p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS and not p.name.startswith(".")),
        key=lambda p: p.name.lower(),
    )
    for name in FOLDER_NAMES:
        for image in images:
            if image.stem.lower() == name:
                return image.read_bytes()
    return images[0].read_bytes() if images else None


@lru_cache(maxsize=64)
def find_cover(path):
    """Returns the cover image (as bytes) for the track at path, or None.

    Looks in the file's own tags first, then for an image in the same folder."""
    try:
        return _embedded_cover(path) or _folder_cover(path.parent)
    except (OSError, ValueError):  # ValueError: øydelagd base64 i OGG-taggar
        return None
