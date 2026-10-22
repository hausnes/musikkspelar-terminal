# musikkspelar-terminal
Ein musikkspelar i terminalen, med litt grom GUI.

Byggd med [Textual](https://textual.textualize.io/) (grensesnitt), [mpv](https://mpv.io/) (avspeling, med gapless overgangar)
og [mutagen](https://mutagen.readthedocs.io/) (lesing av taggar i MP3, FLAC m.fl.).

## Installasjon

```sh
brew install mpv
python3 -m venv .venv
.venv/bin/pip install -e .
```

## Bruk

```sh
.venv/bin/musikkspelar ~/Music
```

Mappa blir skanna rekursivt. Mappestrukturen `Artist/Album/låt.mp3` blir brukt dersom taggane manglar.

| Tast | Handling |
|---|---|
| `Enter` | Spel låta (og resten av albumet) / opne artist eller album / spel låta i køen |
| `Space` | Play / pause |
| `n` / `p` | Neste / førre låt (`p` startar låta på nytt etter 3 sekund) |
| `←` / `→` | Spol 5 sekund bakover / framover (eller klikk på fremdriftslinja) |
| `+` / `-` | Volum opp / ned |
| `a` | Legg låt, album eller artist i køen |
| `x` | Fjern låt frå køen |
| `s` | Stokk av/på |
| `r` | Gjenta: av → alle → éin |
| `c` | Tøm køen |
| `Tab` | Byt mellom bibliotek og kø |
| `q` | Avslutt |

## Struktur

```
musikkspelar/
├── models/          # Rein logikk, utan grensesnitt eller lyd
│   ├── track.py     # Track: ei låt, lagar seg sjølv frå fil
│   ├── library.py   # Library: skannar mappa, grupperer artist → album → låtar
│   └── queue.py     # PlayQueue: rekkjefølgje, stokking og gjenta
├── audio/
│   ├── backend.py   # AudioBackend: abstrakt grensesnitt for lydmotorar
│   └── mpv_backend.py
├── player.py        # Player: koplar køen til lydmotoren og varslar lyttarar
└── ui/              # Textual-appen og widgetane
```

## Testar

```sh
.venv/bin/pip install pytest
.venv/bin/pytest
```
