from musikkspelar.models import PlayQueue, RepeatMode


def make_queue(tracks="ABCDE", start=0):
    queue = PlayQueue()
    queue.replace(list(tracks), start)
    return queue


def test_shuffle_keeps_current_track_and_plays_every_track_once():
    queue = make_queue(start=2)
    queue.toggle_shuffle()
    assert queue.current == "C"
    played = [queue.current] + [queue.advance() for _ in range(4)]
    assert sorted(played) == list("ABCDE")
    assert queue.advance() is None


def test_turning_shuffle_off_keeps_current_track():
    queue = make_queue(start=1)
    queue.toggle_shuffle()
    queue.advance()
    current = queue.current
    queue.toggle_shuffle()
    assert queue.current == current


def test_remove_before_current_keeps_current():
    queue = make_queue(start=1)
    queue.remove(0)
    assert queue.current == "B"


def test_remove_current_moves_to_next():
    queue = make_queue(start=1)
    queue.remove(1)
    assert queue.current == "C"


def test_remove_last_track_empties_queue():
    queue = make_queue("A")
    queue.remove(0)
    assert queue.current is None


def test_repeat_modes():
    queue = make_queue("AB", start=1)
    assert queue.peek_next() is None
    queue.cycle_repeat()
    assert queue.repeat is RepeatMode.ALL
    assert queue.peek_next() == "A"
    queue.cycle_repeat()
    assert queue.repeat is RepeatMode.ONE
    assert queue.peek_next(automatic=True) == "B"   # låta tok slutt av seg sjølv
    assert queue.peek_next(automatic=False) == "A"  # brukaren trykte «neste»


def test_go_back_stops_at_first_track_without_repeat():
    queue = make_queue("AB")
    assert queue.go_back() == "A"
