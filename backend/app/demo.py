from datetime import datetime, timezone
from .schemas import Snapshot


def demo_snapshot() -> Snapshot:
    teams = [{"id": f"demo-{i}", "name": f"Fictional Orbit {i:02}"} for i in range(1, 13)]
    players = []
    for i in range(1, 151):
        rostered = i <= 120
        fgm, threes, ftm = 3 + i % 8, i % 3, 2 + i % 4
        players.append(
            {
                "id": f"fictional-{i}",
                "name": f"Fictional Player {i:03}",
                "positions": ["PG" if i % 2 else "C"],
                "team_id": f"demo-{(i - 1) // 10 + 1}" if rostered else None,
                "availability": "rostered"
                if rostered
                else "waiver"
                if i % 3 == 0
                else "free_agent",
                "stats": {
                    "pts": 2 * fgm + threes + ftm,
                    "reb": 2 + i % 9,
                    "ast": 1 + i % 7,
                    "stl": 1,
                    "blk": i % 3,
                    "threes": threes,
                    "fgm": fgm,
                    "fga": fgm + 5,
                    "ftm": ftm,
                    "fta": ftm + 1,
                    "turnovers": 1 + i % 4,
                },
            }
        )
    return Snapshot(
        mode="demo",
        league_id="demo",
        source="fictional_demo",
        effective_at=datetime.now(timezone.utc),
        stats_horizon="Fictional per-game averages, same demo horizon",
        teams=teams,
        players=players,
    )
