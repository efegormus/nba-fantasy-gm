from .schemas import Player


def category_totals(players: list[Player]) -> dict:
    if any(p.stats is None for p in players):
        raise ValueError("Statistics are missing. Import stats for every rostered player first.")
    sums = {
        key: sum(getattr(p.stats, key) for p in players)
        for key in (
            "pts",
            "reb",
            "ast",
            "stl",
            "blk",
            "threes",
            "fgm",
            "fga",
            "ftm",
            "fta",
            "turnovers",
        )
    }
    return {
        "PTS": sums["pts"],
        "REB": sums["reb"],
        "AST": sums["ast"],
        "STL": sums["stl"],
        "BLK": sums["blk"],
        "3PM": sums["threes"],
        "TO": sums["turnovers"],
        "FG%": sums["fgm"] / sums["fga"] if sums["fga"] else None,
        "FT%": sums["ftm"] / sums["fta"] if sums["fta"] else None,
    }


def category_outcomes(left: dict, right: dict) -> dict:
    return {
        k: None
        if left[k] is None or right[k] is None
        else (
            0
            if left[k] == right[k]
            else (1 if (left[k] < right[k] if k == "TO" else left[k] > right[k]) else -1)
        )
        for k in left
    }
