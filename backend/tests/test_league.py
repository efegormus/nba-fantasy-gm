import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from app.api import create_app
from app.config import Settings
from app.demo import demo_snapshot
from app.providers import parse_import, YahooProvider
from app.schemas import LeagueSetup, Snapshot
from app.service import LeagueService
from app.storage import Base, database

TOKEN = "test-token-" + "x" * 40


@pytest.fixture
def context(tmp_path):
    settings = Settings(
        _env_file=None, database_url=f"sqlite:///{tmp_path}/test.db", local_api_token=TOKEN
    )
    engine, sessions = database(settings.database_url)
    Base.metadata.create_all(engine)
    yield LeagueService(sessions, settings), create_app(settings, sessions)
    engine.dispose()


def real_snapshot(league_id="210163"):
    return Snapshot(
        mode="real",
        league_id=league_id,
        source="manual",
        effective_at=datetime.now(timezone.utc),
        teams=[{"id": "mine", "name": "Imported team"}],
        players=[
            {"id": "p1", "name": "Imported player", "team_id": "mine", "availability": "rostered"},
            {"id": "p2", "name": "Available player", "availability": "free_agent"},
            {"id": "p3", "name": "Waiver player", "availability": "waiver"},
        ],
    )


def test_real_starts_unknown_and_demo_is_isolated(context):
    service, _ = context
    initial = service.status("real")
    assert initial["league_id"] == "210163"
    assert initial["team_count"] is None
    assert initial["setup"]["rules"]["roster_slots"] == {}
    assert initial["setup"]["managed_team_id"] is None
    assert initial["last_successful_refresh"] is None
    service.import_snapshot("demo", demo_snapshot())
    assert service.status("demo")["team_count"] == 12
    assert service.status("real") == initial
    service.import_snapshot("real", real_snapshot())
    assert service.status("real")["team_count"] == 1
    assert service.status("demo")["team_count"] == 12


def test_cross_mode_and_wrong_league_rejected(context):
    service, _ = context
    for snapshot in [demo_snapshot(), real_snapshot("999")]:
        with pytest.raises(ValueError):
            service.import_snapshot("real", snapshot)
    assert service.status("real")["last_successful_refresh"] is None


def test_team_selection_and_league_switch(context):
    service, _ = context
    service.import_snapshot("real", real_snapshot())
    setup = service.setup("real")
    with pytest.raises(ValueError):
        service.save_setup("real", setup.model_copy(update={"managed_team_id": "absent"}))
    setup.managed_team_id = "mine"
    service.save_setup("real", setup)
    assert service.setup("real").managed_team_id == "mine"
    setup.league_url = "https://basketball.fantasysports.yahoo.com/nba/999"
    service.save_setup("real", setup)
    assert service.status("real")["players"] == []
    assert service.setup("real").managed_team_id is None
    setup.league_url = "https://basketball.fantasysports.yahoo.com/nba/210163"
    service.save_setup("real", setup)
    assert service.status("real")["team_count"] == 1


def test_refresh_freshness_and_removal_of_managed_team(context):
    service, _ = context
    snapshot = real_snapshot()
    snapshot.effective_at -= timedelta(days=4)
    service.import_snapshot("real", snapshot)
    assert service.status("real")["freshness"] == "STALE"
    setup = service.setup("real")
    setup.managed_team_id = "mine"
    service.save_setup("real", setup)
    replacement = snapshot.model_dump(mode="json")
    replacement["teams"] = [{"id": "other", "name": "Other"}]
    replacement["players"] = []
    service.import_snapshot("real", Snapshot.model_validate(replacement))
    assert service.setup("real").managed_team_id is None


@pytest.mark.parametrize(
    "mutation",
    [
        lambda d: d.update(source="fictional_demo"),
        lambda d: d["players"].append(d["players"][0]),
        lambda d: d["teams"].append(d["teams"][0]),
        lambda d: d["players"][0].update(team_id="unknown"),
        lambda d: d["players"][1].update(team_id="mine"),
        lambda d: d.update(effective_at="2020-01-01T00:00:00"),
        lambda d: d.update(
            effective_at=(datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        ),
    ],
)
def test_invalid_imports(mutation):
    data = real_snapshot().model_dump(mode="json")
    mutation(data)
    with pytest.raises(ValueError):
        Snapshot.model_validate(data)


def test_csv_and_json():
    snap = real_snapshot()
    assert parse_import(snap.model_dump_json(), "json") == snap
    metadata = snap.model_dump(mode="json", exclude={"teams", "players"})
    csv = "id,name,availability,team_id,team_name,positions\np1,One,rostered,t1,Team,PG|SG\np2,Two,free_agent,,,C\np3,Three,waiver,,,PF\n"
    result = parse_import(csv, "csv", metadata)
    assert len(result.players) == 3
    assert result.players[0].positions == ["PG", "SG"]
    with pytest.raises(ValueError):
        parse_import("id,name\n", "csv", metadata)
    with pytest.raises(ValueError):
        parse_import(csv + "p4,Four,rostered,t1,Conflicting,PG\n", "csv", metadata)


@pytest.mark.parametrize(
    "url",
    [
        "https://evil.test/nba/210163",
        "http://basketball.fantasysports.yahoo.com/nba/210163",
        "https://basketball.fantasysports.yahoo.com/nba/210163/players",
        "https://basketball.fantasysports.yahoo.com/nba/0",
    ],
)
def test_invalid_url(url):
    with pytest.raises(ValueError):
        LeagueSetup(league_url=url)


def test_env_mismatch_and_rules():
    with pytest.raises(ValueError):
        Settings(_env_file=None, yahoo_league_id="42")
    with pytest.raises(ValueError):
        LeagueSetup(
            league_url=Settings(_env_file=None).yahoo_league_url, rules={"roster_slots": {"PG": -1}}
        )
    with pytest.raises(RuntimeError):
        YahooProvider().fetch()


def test_api_authorization_preview_commit_and_validation(context):
    service, app = context
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/api/v1/league").status_code == 401
        client.headers["Authorization"] = "Bearer " + TOKEN
        assert (
            client.get("/api/v1/league", headers={"Origin": "https://evil.test"}).status_code == 403
        )
        assert client.get("/api/v1/league?mode=unknown").status_code == 422
        assert client.get("/api/v1/team").status_code == 409
        data = real_snapshot().model_dump(mode="json")
        preview = client.post(
            "/api/v1/imports/preview", json={"format": "json", "text": json.dumps(data)}
        )
        assert preview.status_code == 200
        assert service.status("real")["last_successful_refresh"] is None
        assert client.post("/api/v1/imports", json=preview.json()).status_code == 200
        timestamp = service.status("real")["last_successful_refresh"]
        data["league_id"] = "other"
        assert client.post("/api/v1/imports", json=data).status_code == 422
        assert service.status("real")["last_successful_refresh"] == timestamp
        assert client.get("/api/v1/recommendations").json()["items"] == []
        assert (
            client.post(
                "/api/v1/imports/preview", json={"format": "json", "text": "invalid"}
            ).status_code
            == 422
        )


def test_persistence(context):
    service, _ = context
    service.import_snapshot("real", real_snapshot())
    other = LeagueService(service.sessions, service.settings)
    assert other.status("real")["team_count"] == 1


def test_agent_api_uses_selected_mode(context):
    service, app = context
    service.import_snapshot("demo", demo_snapshot())
    setup = service.setup("demo")
    setup.managed_team_id = "demo-1"
    service.save_setup("demo", setup)
    with TestClient(app) as client:
        assert client.post("/api/v1/agent/run", json={}).status_code == 401
        client.headers["Authorization"] = "Bearer " + TOKEN
        demo = client.post("/api/v1/agent/run?mode=demo", json={}).json()
        assert demo["observations"]["waiver_scout"]["status"] == "evaluated"
        real = client.post("/api/v1/agent/run?mode=real", json={}).json()
        assert real["league_id"] == "210163"
        assert real["observations"]["waiver_scout"]["status"] == "blocked"
        assert real["observations"]["waiver_scout"]["candidates"] == []
