from pathlib import Path
import httpx
from streamlit.testing.v1 import AppTest


def test_league_setup(monkeypatch):
    status = {
        "connection": "not_connected",
        "freshness": "UNAVAILABLE",
        "team_count": None,
        "last_successful_refresh": None,
        "data_effective_at": None,
        "teams": [],
        "league_id": "210163",
        "setup": {
            "league_url": "https://basketball.fantasysports.yahoo.com/nba/210163",
            "scoring_format": "Head-to-Head 9 Categories",
            "managed_team_id": None,
            "rules": {
                "roster_slots": {},
                "weekly_acquisition_limit": None,
                "waiver_settings": None,
            },
        },
    }

    def request(method, url, **kwargs):
        if url.endswith("/agent/runs"):
            return httpx.Response(200, json={"runs": []}, request=httpx.Request(method, url))
        if url.endswith("/agent/run"):
            return httpx.Response(
                200,
                json={
                    "run_id": 1,
                    "engine": "deterministic_workflow",
                    "data_effective_at": None,
                    "warning": None,
                    "summary": "Import league data first",
                    "trace": [{"tool": "inspect_league", "status": "observed"}],
                    "observations": {"waiver_scout": {"status": "blocked"}},
                },
                request=httpx.Request(method, url),
            )
        return httpx.Response(200, json=status, request=httpx.Request(method, url))

    monkeypatch.setattr(httpx, "request", request)
    app = AppTest.from_file(
        str(Path(__file__).parents[2] / "dashboard/main.py"), default_timeout=30
    ).run()
    assert not app.exception
    assert app.subheader[0].value == "League Setup"
    stamp = next(field.value for field in app.text_input if field.label.startswith("CSV data"))
    app.run()
    assert (
        next(field.value for field in app.text_input if field.label.startswith("CSV data")) == stamp
    )

    app.sidebar.radio[1].set_value("GM Workspace").run()
    assert not app.exception
    app.button[0].click().run()
    assert not app.exception
    assert app.info[0].value == "Import league data first"


def test_current_and_historical_reports_render_together(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from app.api import create_app
    from app.config import Settings
    from app.demo import demo_snapshot
    from app.schemas import NewsEvent
    from app.service import LeagueService
    from app.storage import Base, database

    settings = Settings(
        _env_file=None, database_url=f"sqlite:///{tmp_path}/ui.db", local_api_token="x" * 40
    )
    engine, sessions = database(settings.database_url)
    Base.metadata.create_all(engine)
    service = LeagueService(sessions, settings)
    snapshot = demo_snapshot()
    snapshot.news = [
        NewsEvent(
            id="demo-event",
            player_id="fictional-1",
            headline="Fictional report",
            source_url="https://example.invalid/report",
            published_at=snapshot.effective_at,
        )
    ]
    service.import_snapshot("demo", snapshot)
    setup = service.setup("demo")
    setup.managed_team_id = "demo-1"
    service.save_setup("demo", setup)
    with TestClient(create_app(settings, sessions)) as client:

        def request(method, url, **kwargs):
            return client.request(
                method,
                url.split("8000", 1)[1],
                params=kwargs["params"],
                json=kwargs.get("json"),
                headers={"Authorization": "Bearer " + settings.local_api_token},
            )

        monkeypatch.setattr(httpx, "request", request)
        app = AppTest.from_file(
            str(Path(__file__).parents[2] / "dashboard/main.py"), default_timeout=30
        ).run()
        app.sidebar.radio[0].set_value("demo").run()
        app.sidebar.radio[1].set_value("GM Workspace").run()
        app.button[0].click().run()
        assert not app.exception
        app.selectbox[0].select(1).run()
        assert not app.exception
        assert any("Historical report" in warning.value for warning in app.warning)
        # Existing archive selection stays visible alongside the newly created report.
        app.button[0].click().run()
        assert not app.exception
        app.sidebar.radio[0].set_value("real").run()
        assert not app.exception
        assert not app.selectbox
    engine.dispose()
