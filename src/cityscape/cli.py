from __future__ import annotations

import argparse

from cityscape import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cityscape")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=False)

    hello = sub.add_parser("hello", help="Smoke command to verify installation")
    hello.add_argument("name", nargs="?", default="world")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "hello":
        print(f"hello, {args.name}")
        return 0

    parser.print_help()
    return 0
