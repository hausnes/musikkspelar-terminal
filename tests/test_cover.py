from mutagen.id3 import APIC, ID3

from musikkspelar.models.cover import find_cover


# Ei MPEG-1 Layer III-ramme (128 kbit/s, 44,1 kHz) med stille, så mutagen godtek fila
MP3_FRAME = bytes.fromhex("fffb9064") + bytes(413)


def make_track(folder, name="01.mp3"):
    path = folder / name
    path.write_bytes(MP3_FRAME * 10)
    return path


def test_unreadable_file_still_finds_folder_cover(tmp_path):
    (tmp_path / "cover.jpg").write_bytes(b"front")
    path = tmp_path / "broken.mp3"
    path.write_bytes(b"not audio")
    assert find_cover(path) == b"front"


def test_prefers_cover_named_file_in_folder(tmp_path):
    (tmp_path / "back.jpg").write_bytes(b"back")
    (tmp_path / "Cover.JPG").write_bytes(b"front")
    assert find_cover(make_track(tmp_path)) == b"front"


def test_falls_back_to_any_image_in_folder(tmp_path):
    (tmp_path / "scan.png").write_bytes(b"scan")
    assert find_cover(make_track(tmp_path)) == b"scan"


def test_no_cover(tmp_path):
    assert find_cover(make_track(tmp_path)) is None


def test_embedded_front_cover_wins_over_folder(tmp_path):
    (tmp_path / "cover.jpg").write_bytes(b"folder")
    path = make_track(tmp_path)
    tags = ID3()
    tags.add(APIC(encoding=3, mime="image/jpeg", type=4, desc="Back", data=b"back"))
    tags.add(APIC(encoding=3, mime="image/jpeg", type=3, desc="Front", data=b"embedded"))
    tags.save(path)
    assert find_cover(path) == b"embedded"
