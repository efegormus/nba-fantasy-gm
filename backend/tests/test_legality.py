from datetime import datetime, timedelta, timezone
import pytest
from app.legality import acquisition_check, roster_check
from app.schemas import Player, Rules, Team, Snapshot
from app.demo import demo_snapshot
from app.agent import GMTools
from test_agent import toolset


def player(id, positions, injuries=None):
    return Player(
        id=id,
        name=id,
        positions=positions,
        injury_slots_eligible=injuries,
        availability="free_agent",
    )


def test_flexible_player_does_not_steal_only_slot_from_specialist():
    result = roster_check(
        [player("flex", ["PG", "C"]), player("guard", ["PG"])],
        Rules(roster_slots={"PG": 1, "C": 1}),
    )
    assert result["status"] == "feasible"
    assert result["assignment"] == {"flex": "C", "guard": "PG"}


def test_group_positions_bench_and_impossible_roster():
    assert (
        roster_check(
            [player("g", ["SG"]), player("f", ["SF"])], Rules(roster_slots={"G": 1, "F": 1})
        )["status"]
        == "feasible"
    )
    assert (
        roster_check(
            [player("g", ["PG"]), player("g2", ["PG"])], Rules(roster_slots={"PG": 1, "C": 1})
        )["status"]
        == "infeasible"
    )
    assert (
        roster_check(
            [player("g", ["PG"]), player("g2", ["PG"])], Rules(roster_slots={"PG": 1, "BN": 1})
        )["status"]
        == "feasible"
    )


def test_missing_information_is_not_guessed():
    p = player("unknown", [])
    assert roster_check([p], Rules())["status"] == "unknown"
    assert roster_check([p], Rules(roster_slots={"PG": 1}))["status"] == "unknown"
    assert roster_check([p], Rules(roster_slots={"BN": 1}))["status"] == "feasible"
    assert roster_check([p], Rules(roster_slots={"PG": 0}))["status"] == "infeasible"


def test_injury_slots_require_explicit_eligibility():
    slots = Rules(roster_slots={"IL": 1})
    assert roster_check([player("p", ["C"])], slots)["status"] == "unknown"
    assert roster_check([player("p", ["C"], [])], slots)["status"] == "infeasible"
    assert roster_check([player("p", ["C"], ["IL+"])], slots)["status"] == "infeasible"
    assert roster_check([player("p", ["C"], ["IL"])], slots)["status"] == "feasible"


def test_period_usage_missing_expired_and_exhausted():
    now = datetime.now(timezone.utc)
    rules = Rules(weekly_acquisition_limit=3)
    team = Team(id="team", name="Team")
    assert acquisition_check(team, rules, now)["status"] == "unknown"
    team = Team(
        id="team",
        name="Team",
        acquisitions={
            "used": 3,
            "period_start": now - timedelta(days=1),
            "period_end": now + timedelta(days=1),
        },
    )
    assert acquisition_check(team, rules, now)["status"] == "infeasible"
    assert acquisition_check(team, rules, now + timedelta(days=1))["status"] == "unknown"
    team.acquisitions.used = 2
    assert acquisition_check(team, rules, now)["remaining"] == 1


def test_usage_schema_rejects_missing_timezone_and_wrong_snapshot_period():
    now = datetime.now(timezone.utc)
    with pytest.raises(ValueError):
        Team(
            id="t",
            name="T",
            acquisitions={"used": 1, "period_start": "2026-01-01", "period_end": "2026-01-08"},
        )
    data = demo_snapshot().model_dump(mode="json")
    data["teams"][0]["acquisitions"] = {
        "used": 0,
        "period_start": (now - timedelta(days=8)).isoformat(),
        "period_end": (now - timedelta(days=1)).isoformat(),
    }
    with pytest.raises(ValueError):
        Snapshot.model_validate(data)


def test_agent_excludes_impossible_rosters_and_exhausted_adds():
    tools = toolset()
    tools.status["setup"]["rules"]["roster_slots"] = {"PG": 10}
    waiver = tools.waiver_scout()
    assert waiver["candidates"] == []
    assert waiver["rejected_roster_pairs"] == 300
    trades = tools.trade_analyzer()
    assert trades["candidates"] == []
    assert trades["rejected_roster_pairs"] == 1100
    now = datetime.now(timezone.utc)
    tools.status["setup"]["rules"]["weekly_acquisition_limit"] = 2
    tools.snapshot.teams[0] = Team(
        id="demo-1",
        name="Demo",
        acquisitions={
            "used": 2,
            "period_start": now - timedelta(days=1),
            "period_end": now + timedelta(days=1),
        },
    )
    assert tools.waiver_scout()["status"] == "blocked"


def test_unknown_checks_keep_candidates_provisional():
    result = toolset().waiver_scout()
    assert result["candidates"]
    assert result["candidates"][0]["checks"]["roster"]["status"] == "unknown"
    assert result["candidates"][0]["checks"]["acquisitions"]["status"] == "unknown"
    assert result["candidates"][0]["provisional"] is True
