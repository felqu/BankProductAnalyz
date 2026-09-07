"""CLI entry point for collecting reviews from banki.ru."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Collect a range of review pages from banki.ru."
    )
    parser.add_argument("--start", type=int, required=True, help="First review ID")
    parser.add_argument("--end", type=int, required=True, help="Last review ID (inclusive)")
    parser.add_argument(
        "--write-header",
        action="store_true",
        help="Write a CSV header before results (use for a new output file)",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.start > args.end:
        raise SystemExit("--start must not be greater than --end")
    # Delayed import keeps ``--help`` available before Selenium is installed.
    from parser import main_sync

    main_sync(args.start, args.end, firststart=args.write_header)


if __name__ == "__main__":
    main()
