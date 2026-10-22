# musikkspelar

Ein musikkspelar i terminalen, med litt grom GUI: bibliotek, kø, gapless avspeling,
spektrumanalysator i Winamp-stil og albumcover. Rett i terminalvindauget.

Fungerer på MacOS, Linux og Windows. Krev Python 3.11 eller nyare og ein terminal med fargestøtte
(Terminal.app, iTerm2, Ghostty, Windows Terminal, …).

## Installasjon

Med [uv](https://docs.astral.sh/uv/) (anbefalt – hentar òg riktig Python-versjon):

```sh
uv tool install musikkspelar
```

eller med pipx:

```sh
pipx install musikkspelar
```

Det er alt. Lyden blir spela med [miniaudio](https://github.com/irmen/pyminiaudio), som kjem med pakken.

### Valfritt: mpv

Med [mpv](https://mpv.io/) som lydmotor kan spelaren òg spele M4A og Opus. Installer mpv, og så spelaren med mpv-tillegget:

```sh
brew install mpv                          # macOS
sudo apt install libmpv2                  # Debian/Ubuntu
uv tool install "musikkspelar[mpv]"
```

Spelaren brukar mpv automatisk når det er tilgjengeleg.

## Bruk

```sh
musikkspelar ~/Music
```

Mappa blir skanna rekursivt etter MP3, FLAC, OGG og WAV (pluss M4A og Opus med mpv).
Mappestrukturen `Artist/Album/låt.mp3` blir brukt dersom taggane manglar.

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

Vel lydmotor sjølv med `--lydmotor mpv` eller `--lydmotor miniaudio` (standard: `auto`).

**Albumcover** blir henta frå taggane i fila (MP3, FLAC, M4A, OGG), eller frå eit bilete i albummappa
(`cover.jpg`, `folder.jpg` o.l.). Det blir teikna med halvblokk-teikn (`▀`), så det fungerer i alle
terminalar med fargestøtte.

**Spektrumanalysatoren** dekodar låta ein gong til i bakgrunnen og reknar ut frekvensane med FFT,
i takt med avspelinga.

## Utvikling

Nysgjerrig på korleis alt heng saman? Les [Korleis det heng saman](docs/korleis-det-heng-saman.md):
arkitekturen, trådar, spektrumanalysatoren, albumcover, testing og vegen til PyPI.

```sh
git clone https://github.com/hausnes/musikkspelar-terminal.git
cd musikkspelar-terminal
python3 -m venv .venv
.venv/bin/pip install -e ".[mpv,test]"
.venv/bin/pytest
```

```
musikkspelar/
├── models/              # Rein logikk, utan grensesnitt eller lyd
│   ├── track.py         # Track: ei låt, lagar seg sjølv frå fil
│   ├── library.py       # Library: skannar mappa, grupperer artist → album → låtar
│   ├── queue.py         # PlayQueue: rekkjefølgje, stokking og gjenta
│   └── cover.py         # find_cover(): finn albumcover i fila eller mappa
├── audio/
│   ├── backend.py       # AudioBackend: abstrakt grensesnitt for lydmotorar
│   ├── mpv_backend.py   # MpvBackend: avspeling med libmpv
│   ├── miniaudio_backend.py  # MiniaudioBackend: avspeling utan systemavhengigheiter
│   └── analyzer.py      # SpectrumAnalyzer: frekvensspekter for eit tidspunkt i ei låt
├── player.py            # Player: koplar køen til lydmotoren og varslar lyttarar
└── ui/                  # Textual-appen og widgetane (spectrum.py, cover.py, …)
```

Ny versjon blir publisert til PyPI automatisk når ein lagar ein release på GitHub
(sjå `.github/workflows/publish.yml`).

## Lisens

MIT
