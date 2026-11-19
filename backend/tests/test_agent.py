from datetime import timedelta
import pytest
from app.agent import GMTools, run_workflow
from app.config import Settings
from app.demo import demo_snapshot
from app.schemas import LeagueSetup


def toolset():
    snapshot = demo_snapshot()
    setup = LeagueSetup(
        league_url="https://basketball.fantasysports.yahoo.com/nba/210163", managed_team_id="demo-1"
    )
    status = {
        "mode": "demo",
        "league_id": "demo",
        "freshness": "FRESH",
        "setup": setup.model_dump(),
        "last_successful_refresh": snapshot.effective_at.isoformat(),
        "data_effective_at": snapshot.effective_at.isoformat(),
        "team_count": 12,
    }
    return GMTools(status, snapshot)


def test_tools_report_impacts_without_claiming_legality():
    tools = toolset()
    waiver = tools.waiver_scout()
    assert waiver["status"] == "evaluated"
    assert waiver["candidates"]
    for candidate in waiver["candidates"]:
        assert candidate["provisional"] is True
        assert candidate["heuristic_gain"] > 0
        assert set(candidate["category_changes"]) == {
            "PTS",
            "REB",
            "AST",
            "STL",
            "BLK",
            "3PM",
            "FG%",
            "FT%",
            "TO",
        }
    trade = tools.trade_analyzer()
    assert trade["pairs_examined"] == 1100
    for candidate in trade["candidates"]:
        assert candidate["your_heuristic_gain"] > 0 and candidate["partner_heuristic_gain"] > 0
    assert tools.news_monitor()["events"] == []


@pytest.mark.parametrize(
    "issue", ["stale", "missing_stats", "missing_horizon", "missing_team", "wrong_scoring"]
)
def test_agent_refuses_unsupported_or_missing_data(issue):
    tools = toolset()
    if issue == "stale":
        tools.status["freshness"] = "STALE"
    if issue == "missing_stats":
        tools.snapshot.players[0].stats = None
    if issue == "missing_horizon":
        tools.snapshot.stats_horizon = None
    if issue == "missing_team":
        tools.team_id = None
    if issue == "wrong_scoring":
        tools.status["setup"]["scoring_format"] = "Rotisserie"
    assert tools.waiver_scout()["status"] == "blocked"
    assert tools.trade_analyzer()["status"] == "blocked"


def test_zero_acquisitions_and_invalid_tool():
    tools = toolset()
    tools.status["setup"]["rules"]["weekly_acquisition_limit"] = 0
    assert tools.waiver_scout()["status"] == "blocked"
    with pytest.raises(ValueError):
        tools.call("execute_trade")


def test_offline_workflow_and_local_ai_fallback():
    result = run_workflow(toolset(), Settings(_env_file=None), "Review my team", True)
    assert result["engine"] == "deterministic_workflow"
    assert len(result["trace"]) == 4
    assert result["warning"]


def test_local_ai_is_bounded_and_cannot_execute_transactions():
    settings = Settings(_env_file=None, ollama_enabled=True, ollama_model="local-test")

    def invalid(payload):
        return {"tool_calls": [{"function": {"name": "execute_trade", "arguments": {}}}]}

    result = run_workflow(toolset(), settings, "Make a trade", True, chat=invalid)
    assert result["engine"] == "deterministic_fallback"
    assert all(t["tool"] != "execute_trade" for t in result["trace"])
    calls = []

    def looping(payload):
        calls.append(1)
        return {"tool_calls": [{"function": {"name": "waiver_scout", "arguments": {}}}]}

    result = run_workflow(toolset(), settings, "Review", True, chat=looping)
    assert len(calls) == 4
    assert len(result["trace"]) == 4
    assert result["engine"] == "local_ollama_tool_selection"


def test_news_requires_evidence_and_valid_player():
    snapshot = demo_snapshot()
    data = snapshot.model_dump(mode="json")
    event = {
        "id": "event-1",
        "player_id": "fictional-1",
        "headline": "Fictional injury report",
        "source_url": "https://example.invalid/report",
        "published_at": (snapshot.effective_at - timedelta(hours=1)).isoformat(),
    }
    data["news"] = [event]
    validated = type(snapshot).model_validate(data)
    tools = toolset()
    tools.snapshot = validated
    assert tools.news_monitor()["events"][0]["verification"] == "unverified"
    event["player_id"] = "unknown"
    with pytest.raises(ValueError):
        type(snapshot).model_validate(data)


def test_cross_scope_context_is_rejected():
    tools = toolset()
    tools.status["mode"] = "real"
    tools.status["league_id"] = "210163"
    with pytest.raises(ValueError):
        GMTools(tools.status, tools.snapshot)
