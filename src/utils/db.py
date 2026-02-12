from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

import psycopg2
import psycopg2.extras


@dataclass(frozen=True, slots=True)
class PostgresConfig:
    host: str
    port: int
    user: str
    password: str
    dbname: str


def connect(cfg: PostgresConfig):
    return psycopg2.connect(
        host=cfg.host,
        port=cfg.port,
        user=cfg.user,
        password=cfg.password,
        dbname=cfg.dbname,
    )


def ensure_raw_schema(conn) -> None:
    with conn.cursor() as cur:
        cur.execute("create schema if not exists raw")


def ensure_mlb_tables(conn) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            create table if not exists raw.mlb_teams (
              team_id integer not null,
              season integer not null,
              team_name varchar not null,
              team_abbr varchar null,
              league_id integer null,
              division_id integer null,
              raw jsonb not null,
              loaded_at timestamptz not null default now(),
              primary key (team_id, season)
            );
            """
        )
        cur.execute(
            """
            create table if not exists raw.mlb_games (
              game_id bigint not null,
              season integer not null,
              game_date date null,
              game_type varchar null,
              status varchar null,
              home_team_id integer null,
              away_team_id integer null,
              home_score integer null,
              away_score integer null,
              raw jsonb not null,
              loaded_at timestamptz not null default now(),
              primary key (game_id, season)
            );
            """
        )
        cur.execute(
            """
            create table if not exists raw.mlb_standings (
              team_id integer not null,
              season integer not null,
              standings_date date not null,
              league_id integer null,
              division_id integer null,
              division_rank integer null,
              wins integer null,
              losses integer null,
              win_pct float null,
              games_back float null,
              wildcard_games_back float null,
              streak varchar null,
              last_ten_record varchar null,
              runs_scored integer null,
              runs_allowed integer null,
              run_differential integer null,
              home_wins integer null,
              home_losses integer null,
              away_wins integer null,
              away_losses integer null,
              raw jsonb not null,
              loaded_at timestamptz not null default now(),
              primary key (team_id, season, standings_date)
            );
            """
        )


def upsert_mlb_teams(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
    insert into raw.mlb_teams (
      team_id, season, team_name, team_abbr, league_id, division_id, raw
    ) values (
      %(team_id)s, %(season)s, %(team_name)s, %(team_abbr)s, %(league_id)s, %(division_id)s, %(raw)s
    )
    on conflict (team_id, season) do update set
      team_name = excluded.team_name,
      team_abbr = excluded.team_abbr,
      league_id = excluded.league_id,
      division_id = excluded.division_id,
      raw = excluded.raw,
      loaded_at = now()
    """

    payload = []
    for r in rows:
        payload.append(
            {
                **r,
                "raw": psycopg2.extras.Json(r["raw"]),
            }
        )

    if not payload:
        return 0

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, payload, page_size=500)
    return len(payload)


def upsert_mlb_games(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
    insert into raw.mlb_games (
      game_id, season, game_date, game_type, status,
      home_team_id, away_team_id, home_score, away_score, raw
    ) values (
      %(game_id)s, %(season)s, %(game_date)s, %(game_type)s, %(status)s,
      %(home_team_id)s, %(away_team_id)s, %(home_score)s, %(away_score)s, %(raw)s
    )
    on conflict (game_id, season) do update set
      game_date = excluded.game_date,
      game_type = excluded.game_type,
      status = excluded.status,
      home_team_id = excluded.home_team_id,
      away_team_id = excluded.away_team_id,
      home_score = excluded.home_score,
      away_score = excluded.away_score,
      raw = excluded.raw,
      loaded_at = now()
    """

    payload = []
    for r in rows:
        payload.append(
            {
                **r,
                "raw": psycopg2.extras.Json(r["raw"]),
            }
        )

    if not payload:
        return 0

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, payload, page_size=500)
    return len(payload)


def upsert_mlb_standings(conn, rows: Iterable[dict[str, Any]]) -> int:
    sql = """
    insert into raw.mlb_standings (
      team_id, season, standings_date, league_id, division_id, division_rank,
      wins, losses, win_pct, games_back, wildcard_games_back,
      streak, last_ten_record, runs_scored, runs_allowed, run_differential,
      home_wins, home_losses, away_wins, away_losses, raw
    ) values (
      %(team_id)s, %(season)s, %(standings_date)s, %(league_id)s, %(division_id)s, %(division_rank)s,
      %(wins)s, %(losses)s, %(win_pct)s, %(games_back)s, %(wildcard_games_back)s,
      %(streak)s, %(last_ten_record)s, %(runs_scored)s, %(runs_allowed)s, %(run_differential)s,
      %(home_wins)s, %(home_losses)s, %(away_wins)s, %(away_losses)s, %(raw)s
    )
    on conflict (team_id, season, standings_date) do update set
      league_id = excluded.league_id,
      division_id = excluded.division_id,
      division_rank = excluded.division_rank,
      wins = excluded.wins,
      losses = excluded.losses,
      win_pct = excluded.win_pct,
      games_back = excluded.games_back,
      wildcard_games_back = excluded.wildcard_games_back,
      streak = excluded.streak,
      last_ten_record = excluded.last_ten_record,
      runs_scored = excluded.runs_scored,
      runs_allowed = excluded.runs_allowed,
      run_differential = excluded.run_differential,
      home_wins = excluded.home_wins,
      home_losses = excluded.home_losses,
      away_wins = excluded.away_wins,
      away_losses = excluded.away_losses,
      raw = excluded.raw,
      loaded_at = now()
    """

    payload = []
    for r in rows:
        payload.append(
            {
                **r,
                "raw": psycopg2.extras.Json(r["raw"]),
            }
        )

    if not payload:
        return 0

    with conn.cursor() as cur:
        psycopg2.extras.execute_batch(cur, sql, payload, page_size=500)
    return len(payload)
