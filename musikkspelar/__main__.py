import argparse
from pathlib import Path

from .audio import BACKENDS


def main():
    parser = argparse.ArgumentParser(prog="musikkspelar", description="Ein musikkspelar i terminalen.")
    parser.add_argument("mappe", nargs="?", default="~/Music", help="mappa med musikk (standard: ~/Music)")
    parser.add_argument(
        "--lydmotor",
        choices=("auto", *BACKENDS),
        default="auto",
        help="auto (standard) brukar mpv dersom det er installert, elles miniaudio",
    )
    args = parser.parse_args()

    folder = Path(args.mappe).expanduser()
    if not folder.is_dir():
        parser.error(f"fann ikkje mappa {folder}")

    from .audio import create_backend
    from .ui.app import MusicPlayerApp

    try:
        backend = create_backend(args.lydmotor)
    except (ImportError, OSError) as error:
        parser.error(f"kunne ikkje starte lydmotoren {args.lydmotor}: {error}")
    MusicPlayerApp(folder, backend).run()


if __name__ == "__main__":
    main()
