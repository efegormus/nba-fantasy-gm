import os
import subprocess
import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from app.api import create_app
from app.config import Settings
from app.demo import demo_snapshot
from app.schemas import LeagueSetup
from app.service import LeagueService
from app.storage import Base, database

TOKEN = "history-test-" + "z" * 32


@pytest.fixture
def context(tmp_path):
    settings = Settings(
        _env_file=None, database_url=f"sqlite:///{tmp_path}/history.db", local_api_token=TOKEN
    )
    engine, sessions = database(settings.database_url)
    Base.metadata.create_all(engine)
    service = LeagueService(sessions, settings)
    with TestClient(
        create_app(settings, sessions), headers={"Authorization": "Bearer " + TOKEN}
    ) as client:
        yield service, client, settings, sessions
    engine.dispose()


def test_report_preserves_evidence_and_settings_across_imports_and_restart(context):
    service, client, settings, sessions = context
    snapshot = demo_snapshot()
    service.import_snapshot("demo", snapshot)
    setup = service.setup("demo")
    setup.managed_team_id = "demo-1"
    service.save_setup("demo", setup)
    result = client.post("/api/v1/agent/run?mode=demo", json={"question": "Find waiver ideas"})
    assert result.status_code == 200
    run_id = result.json()["run_id"]
    original = client.get(f"/api/v1/agent/runs/{run_id}?mode=demo").json()
    snapshot.players[0].name = "Changed after the analysis"
    service.import_snapshot("demo", snapshot)
    setup.managed_team_id = "demo-2"
    service.save_setup("demo", setup)
    with TestClient(
        create_app(settings, sessions), headers={"Authorization": "Bearer " + TOKEN}
    ) as restarted:
        saved = restarted.get(f"/api/v1/agent/runs/{run_id}?mode=demo").json()
        assert saved == original
        assert saved["evidence"]["players"][0]["name"] != snapshot.players[0].name
        assert saved["context"]["setup"]["managed_team_id"] == "demo-1"
        assert saved["historical"] is True
        assert saved["snapshot_id"] != service.latest("demo").id


def test_history_is_scoped_authorized_and_bounded(context):
    service, client, _, _ = context
    demo = client.post("/api/v1/agent/run?mode=demo", json={}).json()["run_id"]
    real = client.post("/api/v1/agent/run?mode=real", json={}).json()["run_id"]
    assert client.get(f"/api/v1/agent/runs/{demo}?mode=real").status_code == 404
    assert client.get(f"/api/v1/agent/runs/{real}?mode=demo").status_code == 404
    assert len(client.get("/api/v1/agent/runs?mode=real").json()["runs"]) == 1
    assert client.get("/api/v1/agent/runs?limit=101").status_code == 422
    assert client.get("/api/v1/agent/runs", headers={"Authorization": "invalid"}).status_code == 401
    assert (
        client.get(f"/api/v1/agent/runs/{real}", headers={"Authorization": "invalid"}).status_code
        == 401
    )
    service.save_setup(
        "real", LeagueSetup(league_url="https://basketball.fantasysports.yahoo.com/nba/999")
    )
    assert client.get("/api/v1/agent/runs").json()["runs"] == []
    assert client.get(f"/api/v1/agent/runs/{real}").status_code == 404
    service.save_setup(
        "real", LeagueSetup(league_url="https://basketball.fantasysports.yahoo.com/nba/210163")
    )
    saved = client.get(f"/api/v1/agent/runs/{real}").json()
    assert saved["evidence"] is None
    assert saved["report"]["observations"]["waiver_scout"]["status"] == "blocked"


def test_newest_first_and_limit(context):
    _, client, _, _ = context
    ids = [
        client.post("/api/v1/agent/run", json={"question": f"Question {i}"}).json()["run_id"]
        for i in range(3)
    ]
    rows = client.get("/api/v1/agent/runs?limit=2").json()["runs"]
    assert [r["id"] for r in rows] == ids[-1:-3:-1]
    assert "evidence" not in rows[0]


def test_migration_preserves_existing_snapshot(tmp_path):
    root = Path(__file__).parents[2]
    url = f"sqlite:///{tmp_path}/migration.db"
    env = {**os.environ, "DATABASE_URL": url}

    def migrate(revision):
        subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", revision],
            cwd=root,
            env=env,
            check=True,
            capture_output=True,
        )

    migrate("0001")
    engine, _ = database(url)
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO import_snapshot (scope, imported_at, data) VALUES (:scope, :at, :data)"
            ),
            {"scope": "demo", "at": "2026-01-01", "data": '{"marker":"preserve"}'},
        )
    migrate("head")
    migrate("head")
    with engine.connect() as connection:
        assert (
            connection.execute(text("SELECT data FROM import_snapshot")).scalar_one()
            == '{"marker":"preserve"}'
        )
        assert connection.execute(text("SELECT COUNT(*) FROM agent_run")).scalar_one() == 0
    engine.dispose()
