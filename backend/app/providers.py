"""Providers never infer access from a public league identifier."""

import csv
import io
import json
from typing import Protocol
from .schemas import Snapshot


class FantasyLeagueProvider(Protocol):
    def fetch(self) -> Snapshot: ...


class YahooProvider:
    def fetch(self) -> Snapshot:
        raise RuntimeError(
            "Yahoo API disabled. Use manual import; approved user-initiated OAuth is not implemented."
        )


def parse_import(text: str, file_format: str, metadata: dict | None = None) -> Snapshot:
    if len(text.encode()) > 5_000_000:
        raise ValueError("Import must be smaller than 5 MB")
    if file_format == "json":
        return Snapshot.model_validate(json.loads(text))
    if file_format != "csv" or metadata is None:
        raise ValueError("CSV requires mode, league_id, source and effective_at metadata")
    reader = csv.DictReader(io.StringIO(text))
    required = {"id", "name", "availability", "team_id", "team_name", "positions"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("CSV requires columns: " + ", ".join(sorted(required)))
    teams, players = {}, []
    for row in reader:
        tid = row["team_id"].strip() or None
        if tid:
            name = row["team_name"].strip()
            if tid in teams and teams[tid] != name:
                raise ValueError("Conflicting names for the same team ID")
            teams[tid] = name
        players.append(
            {
                "id": row["id"],
                "name": row["name"],
                "availability": row["availability"],
                "team_id": tid,
                "positions": [p.strip() for p in row["positions"].split("|") if p.strip()],
                "yahoo_id": row.get("yahoo_id") or None,
                "nba_id": row.get("nba_id") or None,
            }
        )
    return Snapshot.model_validate(
        {**metadata, "teams": [{"id": k, "name": v} for k, v in teams.items()], "players": players}
    )
