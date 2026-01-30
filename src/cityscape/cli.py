from __future__ import annotations

import argparse

from cityscape import __version__
from cityscape.automations.ingest.mlb import ingest_mlb_season


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cityscape")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=False)

    hello = sub.add_parser("hello", help="Smoke command to verify installation")
    hello.add_argument("name", nargs="?", default="world")

    ingest = sub.add_parser("ingest", help="Ingest raw data from external APIs")
    ingest_sub = ingest.add_subparsers(dest="ingest_target", required=True)

    ingest_mlb = ingest_sub.add_parser("mlb", help="Fetch MLB season data and land it into Postgres")
    ingest_mlb.add_argument("--season", type=int, required=True, help="Season year, e.g. 2024")
    ingest_mlb.add_argument(
        "--game-types",
        default="R",
        help="Comma-separated gameTypes for MLB Stats API (default: R=regular season)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "hello":
        print(f"hello, {args.name}")
        return 0

    if args.command == "ingest" and args.ingest_target == "mlb":
        teams, games = ingest_mlb_season(season=args.season, game_types=args.game_types)
        print(f"ingested mlb season={args.season}: teams={teams} games={games}")
        return 0

    parser.print_help()
    return 0
