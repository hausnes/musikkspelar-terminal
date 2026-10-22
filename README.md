# musikkspelar-terminal
Ein musikkspelar i terminalen, med litt grom GUI.

Byggd med [Textual](https://textual.textualize.io/) (grensesnitt), [mpv](https://mpv.io/) (avspeling, med gapless overgangar)
og [mutagen](https://mutagen.readthedocs.io/) (lesing av taggar i MP3, FLAC m.fl.).
Spektrumanalysatoren dekodar låta ein gong til med [miniaudio](https://github.com/irmen/pyminiaudio)
og reknar ut frekvensane med numpy (FFT), i takt med posisjonen til mpv.

Albumcover blir henta frå taggane i fila (MP3, FLAC, M4A, OGG), eller frå eit bilete i albummappa
(`cover.jpg`, `folder.jpg` o.l.). Det blir teikna med halvblokk-teikn (`▀`), så det fungerer i alle
terminalar med fargestøtte, også Terminal.app.

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
| `v` | Spektrumanalysator av/på |
| `i` | Vis albumcoveret stort |
| `c` | Tøm køen |
| `Tab` | Byt mellom bibliotek og kø |
| `q` | Avslutt |

## Struktur

```
musikkspelar/
├── models/          # Rein logikk, utan grensesnitt eller lyd
│   ├── track.py     # Track: ei låt, lagar seg sjølv frå fil
│   ├── library.py   # Library: skannar mappa, grupperer artist → album → låtar
│   ├── queue.py     # PlayQueue: rekkjefølgje, stokking og gjenta
│   └── cover.py     # find_cover(): finn albumcover i fila eller mappa
├── audio/
│   ├── backend.py   # AudioBackend: abstrakt grensesnitt for lydmotorar
│   ├── mpv_backend.py
│   └── analyzer.py  # SpectrumAnalyzer: frekvensspekter for eit gitt tidspunkt i ei låt
├── player.py        # Player: koplar køen til lydmotoren og varslar lyttarar
└── ui/              # Textual-appen og widgetane (spectrum.py: Winamp-søylene, cover.py: albumcover)
```

## Testar

```sh
.venv/bin/pip install pytest
.venv/bin/pytest
```
