import pytest
from app.analytics import category_totals, category_outcomes
from app.schemas import Player, Stats


def player(id, **stats):
    values = {key: 0 for key in Stats.model_fields}
    values.update(stats)
    return Player(id=id, name=id, availability="free_agent", stats=Stats(**values))


def test_volume_weighted_shooting_and_counts():
    totals = category_totals(
        [
            player("1", fgm=1, fga=2, ftm=1, fta=2, pts=3),
            player("2", fgm=9, fga=10, ftm=9, fta=10, pts=27),
        ]
    )
    assert totals["FG%"] == pytest.approx(10 / 12)
    assert totals["FT%"] == pytest.approx(10 / 12)
    assert totals["PTS"] == 30


def test_zero_attempts_and_turnover_direction():
    totals = category_totals([player("1", turnovers=1)])
    assert totals["FG%"] is None
    other = category_totals([player("2", turnovers=3)])
    assert category_outcomes(totals, other)["TO"] == 1
    assert category_outcomes(totals, other)["PTS"] == 0
    assert category_outcomes(totals, other)["FT%"] is None


def test_missing_and_invalid_stats():
    with pytest.raises(ValueError):
        category_totals([Player(id="1", name="1", availability="free_agent")])
    for invalid in [
        {"fgm": 3, "fga": 2},
        {"ftm": 2, "fta": 1},
        {"pts": -1},
        {"pts": float("nan")},
        {"threes": 5, "fgm": 2, "fga": 3},
    ]:
        with pytest.raises(ValueError):
            values = {key: 0 for key in Stats.model_fields}
            values.update(invalid)
            Stats(**values)
