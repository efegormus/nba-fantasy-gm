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
        if url.endswith("/agent/run"):
            return httpx.Response(
                200,
                json={
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
