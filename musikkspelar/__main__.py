import argparse
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(prog="musikkspelar", description="Ein musikkspelar i terminalen.")
    parser.add_argument("mappe", nargs="?", default="~/Music", help="mappa med musikk (standard: ~/Music)")
    args = parser.parse_args()

    folder = Path(args.mappe).expanduser()
    if not folder.is_dir():
        parser.error(f"fann ikkje mappa {folder}")

    from .ui.app import MusicPlayerApp  # importerast her så --help ikkje treng libmpv
    MusicPlayerApp(folder).run()


if __name__ == "__main__":
    main()
