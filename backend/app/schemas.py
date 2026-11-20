from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator
from .config import league_id_from_url

Mode = Literal["demo", "real"]
CATEGORIES = ["PTS", "REB", "AST", "STL", "BLK", "3PM", "FG%", "FT%", "TO"]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Rules(StrictModel):
    roster_slots: dict[str, int] = Field(default_factory=dict)
    weekly_acquisition_limit: int | None = Field(default=None, ge=0)
    waiver_settings: str | None = Field(default=None, max_length=2000)

    @field_validator("roster_slots")
    @classmethod
    def valid_slots(cls, slots):
        allowed = {"PG", "SG", "G", "SF", "PF", "F", "C", "UTIL", "BN", "IL", "IL+"}
        if any(
            k not in allowed or type(v) is not int or v < 0 or v > 100 for k, v in slots.items()
        ):
            raise ValueError("Roster slots must use supported positions and integer counts 0–100")
        return slots


class LeagueSetup(StrictModel):
    league_url: str
    scoring_format: Literal["Head-to-Head 9 Categories", "Head-to-Head Points", "Rotisserie"] = (
        "Head-to-Head 9 Categories"
    )
    rules: Rules = Field(default_factory=Rules)
    managed_team_id: str | None = None

    @field_validator("league_url")
    @classmethod
    def valid_url(cls, value):
        league_id_from_url(value)
        return value.strip().rstrip("/")


class AcquisitionUsage(StrictModel):
    used: int = Field(ge=0)
    period_start: datetime
    period_end: datetime

    @model_validator(mode="after")
    def valid_period(self):
        if self.period_start.tzinfo is None or self.period_end.tzinfo is None:
            raise ValueError("Acquisition period boundaries require timezones")
        if self.period_start >= self.period_end:
            raise ValueError("Acquisition period end must follow its start")
        return self


class Team(StrictModel):
    acquisitions: AcquisitionUsage | None = None
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)


class Stats(StrictModel):
    pts: float = Field(ge=0)
    reb: float = Field(ge=0)
    ast: float = Field(ge=0)
    stl: float = Field(ge=0)
    blk: float = Field(ge=0)
    threes: float = Field(ge=0)
    fgm: float = Field(ge=0)
    fga: float = Field(ge=0)
    ftm: float = Field(ge=0)
    fta: float = Field(ge=0)
    turnovers: float = Field(ge=0)

    @model_validator(mode="after")
    def shooting(self):
        if self.fgm > self.fga or self.ftm > self.fta or self.threes > self.fgm:
            raise ValueError(
                "Shot makes cannot exceed attempts; threes cannot exceed field goals made"
            )
        return self


class Player(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=200)
    yahoo_id: str | None = None
    nba_id: str | None = None
    positions: list[Literal["PG", "SG", "SF", "PF", "C", "G", "F", "UTIL"]] = Field(
        default_factory=list
    )
    injury_slots_eligible: list[Literal["IL", "IL+"]] | None = None
    team_id: str | None = None
    availability: Literal["rostered", "free_agent", "waiver"]
    stats: Stats | None = None

    @model_validator(mode="after")
    def ownership(self):
        if (self.availability == "rostered") != (self.team_id is not None):
            raise ValueError("Only rostered players must have a team_id")
        return self


class NewsEvent(StrictModel):
    event_type: Literal[
        "OTHER",
        "PLAYER_OUT",
        "PLAYER_QUESTIONABLE",
        "PLAYER_RETURN",
        "ROLE_INCREASE",
        "ROLE_DECREASE",
    ] = "OTHER"
    id: str = Field(min_length=1, max_length=100)
    player_id: str
    headline: str = Field(min_length=1, max_length=500)
    source_url: HttpUrl
    published_at: datetime
    verification: Literal["unverified", "user_verified"] = "unverified"

    @field_validator("published_at")
    @classmethod
    def valid_publication(cls, value):
        if value.tzinfo is None or value > datetime.now(timezone.utc):
            raise ValueError("News publication must have a timezone and cannot be in the future")
        return value


class Snapshot(StrictModel):
    mode: Mode
    league_id: str
    stats_horizon: str | None = Field(default=None, min_length=1, max_length=300)
    news: list[NewsEvent] = Field(default_factory=list, max_length=100)
    source: Literal["manual", "fictional_demo"]
    effective_at: datetime
    teams: list[Team] = Field(min_length=1, max_length=100)
    players: list[Player] = Field(max_length=10000)

    @model_validator(mode="after")
    def integrity(self):
        if self.effective_at.tzinfo is None or self.effective_at > datetime.now(timezone.utc):
            raise ValueError("effective_at must be timezone-aware and cannot be in the future")
        if (self.mode == "demo") != (self.source == "fictional_demo"):
            raise ValueError("Demo and real data provenance cannot be mixed")
        if self.mode == "demo" and self.league_id != "demo":
            raise ValueError("Demo data must use the demo league ID")
        for values, label in [(self.teams, "team"), (self.players, "player")]:
            if len({v.id for v in values}) != len(values):
                raise ValueError(f"Duplicate {label} IDs")
        if any(event.published_at > self.effective_at for event in self.news):
            raise ValueError("News cannot postdate the snapshot effective timestamp")
        players = {p.id for p in self.players}
        if len({event.id for event in self.news}) != len(self.news):
            raise ValueError("Duplicate news event IDs")
        if any(event.player_id not in players for event in self.news):
            raise ValueError("News references an unknown player")
        for team in self.teams:
            if team.acquisitions and not (
                team.acquisitions.period_start <= self.effective_at < team.acquisitions.period_end
            ):
                raise ValueError(
                    "Acquisition usage period must contain the snapshot effective timestamp"
                )
        teams = {t.id for t in self.teams}
        if any(p.team_id is not None and p.team_id not in teams for p in self.players):
            raise ValueError("Player references an unknown team")
        for key in ("yahoo_id", "nba_id"):
            ids = [getattr(p, key) for p in self.players if getattr(p, key)]
            if len(ids) != len(set(ids)):
                raise ValueError(f"Duplicate {key}")
        return self
