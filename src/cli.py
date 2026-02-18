from __future__ import annotations

import argparse
from datetime import datetime

from src import __version__
from src.automations.ingest.mlb import ingest_mlb_schedule_bigquery, ingest_mlb_season_bigquery


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cityscape")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=False)

    hello = sub.add_parser("hello", help="Smoke command to verify installation")
    hello.add_argument("name", nargs="?", default="world")

    ingest = sub.add_parser("ingest", help="Ingest raw data from external APIs")
    ingest_sub = ingest.add_subparsers(dest="ingest_target", required=True)

    ingest_mlb = ingest_sub.add_parser("mlb", help="Ingest MLB raw data into BigQuery")
    ingest_mlb.add_argument(
        "action",
        nargs="?",
        default="season",
        choices=["season", "schedule"],
        help="Which MLB dataset to ingest (default: season)",
    )
    ingest_mlb.add_argument("--season", type=int, required=True, help="Season year, e.g. 2024")
    ingest_mlb.add_argument(
        "--game-types",
        default="R,F,D,L,W,S",
        help="Comma-separated gameTypes for MLB Stats API (default: R,F,D,L,W,S)",
    )
    ingest_mlb.add_argument(
        "--start-date",
        type=str,
        default=None,
        help="Optional start date filter (YYYY-MM-DD)",
    )
    ingest_mlb.add_argument(
        "--end-date",
        type=str,
        default=None,
        help="Optional end date filter (YYYY-MM-DD)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "hello":
        print(f"hello, {args.name}")
        return 0

    if args.command == "ingest" and args.ingest_target == "mlb":
        start_date = (
            datetime.strptime(args.start_date, "%Y-%m-%d").date() if args.start_date else None
        )
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d").date() if args.end_date else None

        if args.action == "schedule":
            schedule, broadcasts, lineups = ingest_mlb_schedule_bigquery(
                season=args.season,
                game_types=args.game_types,
                start_date=start_date,
                end_date=end_date,
            )
            print(
                f"ingested mlb schedule={args.season}: schedule={schedule} broadcasts={broadcasts} lineups={lineups}"
            )
            return 0

        teams, games, leagues, divisions = ingest_mlb_season_bigquery(
            season=args.season,
            game_types=args.game_types,
            start_date=start_date,
            end_date=end_date,
        )
        print(
            f"ingested mlb season={args.season}: teams={teams} games={games} leagues={leagues} divisions={divisions}"
        )
        return 0

    parser.print_help()
    return 0
