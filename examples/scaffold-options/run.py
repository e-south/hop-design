"""Reproduce explicitly chosen public scaffold options using the installed HOP API."""

import argparse
from pathlib import Path

from hop_design import construction


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--endpoint", choices=("insert", "hairpin"), required=True)
    parser.add_argument("--max-continuations", type=int, required=True)
    parser.add_argument("--option", action="append", required=True)
    parser.add_argument("--baseline", required=True)
    args = parser.parse_args()
    if args.out.exists() or args.out.is_symlink():
        parser.error("Output already exists; use a new directory.")
    source = Path(__file__).resolve().parent
    options = construction.explore_construction_options(
        source / f"{args.endpoint}.json", max_continuations=args.max_continuations
    )
    options_path = options.write(args.out / "options")
    construction.find_construction_option_sets(options_path, source / "comparison.json").write(
        args.out / "groups"
    )
    construction.select_construction_options(
        options_path,
        option_labels=tuple(args.option),
        baseline=args.baseline,
        comparison=source / "comparison.json",
    ).write(args.out / "selected")
    print(args.out / "selected/report.pdf")


if __name__ == "__main__":
    main()
