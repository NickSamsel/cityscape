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
