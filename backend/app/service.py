from datetime import datetime, timezone
from sqlalchemy import select
from .config import Settings, league_id_from_url
from .schemas import LeagueSetup, Mode, Rules, Snapshot
from .storage import Configuration, ImportSnapshot


class LeagueService:
    def __init__(self, sessions, settings: Settings):
        self.sessions, self.settings = sessions, settings

    def setup(self, mode: Mode) -> LeagueSetup:
        with self.sessions() as session:
            record = session.get(Configuration, mode)
            return (
                LeagueSetup.model_validate(record.data)
                if record
                else LeagueSetup(league_url=self.settings.yahoo_league_url)
            )

    def scope(self, mode: Mode) -> str:
        return (
            "demo" if mode == "demo" else "real:" + league_id_from_url(self.setup(mode).league_url)
        )

    def latest(self, mode: Mode):
        with self.sessions() as session:
            return session.scalar(
                select(ImportSnapshot)
                .where(ImportSnapshot.scope == self.scope(mode))
                .order_by(ImportSnapshot.id.desc())
                .limit(1)
            )

    def save_setup(self, mode: Mode, setup: LeagueSetup):
        old = self.setup(mode)
        if mode == "real" and old.league_url != setup.league_url:
            # Changing leagues never carries a managed team or rules from the old league.
            setup = setup.model_copy(update={"managed_team_id": None, "rules": Rules()})
        if setup.managed_team_id:
            record = self.latest(mode)
            if not record or setup.managed_team_id not in {t["id"] for t in record.data["teams"]}:
                raise ValueError("Select a team from the current league import")
        with self.sessions.begin() as session:
            session.merge(Configuration(scope=mode, data=setup.model_dump()))
        return setup

    def validate(self, mode: Mode, snapshot: Snapshot):
        target = "demo" if mode == "demo" else league_id_from_url(self.setup(mode).league_url)
        if snapshot.mode != mode or snapshot.league_id != target:
            raise ValueError("Import mode or league ID does not match the configured target")

    def import_snapshot(self, mode: Mode, snapshot: Snapshot):
        self.validate(mode, snapshot)
        scope = self.scope(mode)
        with self.sessions.begin() as session:
            record = ImportSnapshot(scope=scope, data=snapshot.model_dump(mode="json"))
            session.add(record)
            config = self.setup(mode)
            if config.managed_team_id not in {t.id for t in snapshot.teams}:
                config.managed_team_id = None
                session.merge(Configuration(scope=mode, data=config.model_dump()))
        return self.status(mode)

    def status(self, mode: Mode, record=...) -> dict:
        setup = self.setup(mode)
        if record is ...:
            record = self.latest(mode)
        effective = datetime.fromisoformat(record.data["effective_at"]) if record else None
        age = (datetime.now(timezone.utc) - effective).total_seconds() if effective else None
        freshness = (
            "UNAVAILABLE"
            if age is None
            else "FRESH"
            if age < 86400
            else "AGING"
            if age < 172800
            else "STALE"
        )
        return {
            "mode": mode,
            "league_id": "demo" if mode == "demo" else league_id_from_url(setup.league_url),
            "setup": setup.model_dump(),
            "connection": "fictional_demo"
            if mode == "demo" and record
            else "manual_import"
            if record
            else "not_connected",
            "yahoo_api": "disabled",
            "freshness": freshness,
            "last_successful_refresh": record.imported_at.replace(tzinfo=timezone.utc).isoformat()
            if record
            else None,
            "data_effective_at": effective.isoformat() if effective else None,
            "team_count": len(record.data["teams"]) if record else None,
            "teams": record.data["teams"] if record else [],
            "players": record.data["players"] if record else [],
        }
