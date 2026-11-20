"""Partial feasibility checks; never claims a Yahoo transaction is executable."""

from collections import deque
from datetime import datetime, timezone
from .schemas import Player, Rules, Team

GROUPS = {"G": {"PG", "SG", "G"}, "F": {"SF", "PF", "F"}}


def eligible(player: Player, slot: str, optimistic: bool) -> bool:
    if slot in {"IL", "IL+"}:
        return (
            optimistic
            if player.injury_slots_eligible is None
            else slot in player.injury_slots_eligible
        )
    if slot in {"UTIL", "BN"}:
        return True
    if not player.positions:
        return optimistic
    return slot in player.positions or bool(GROUPS.get(slot, set()) & set(player.positions))


def match(players, slots, optimistic=False):
    """Maximum bipartite matching via augmenting paths, no greedy position assumptions."""
    owners, assigned = {}, {}
    for root in range(len(players)):
        queue, visited, parents = deque([root]), {root}, {}
        endpoint = None
        while queue and endpoint is None:
            current = queue.popleft()
            for index, slot in enumerate(slots):
                if not eligible(players[current], slot, optimistic):
                    continue
                if index not in owners:
                    endpoint = (current, index)
                    break
                owner = owners[index]
                if owner not in visited:
                    visited.add(owner)
                    parents[owner] = (current, index)
                    queue.append(owner)
        if endpoint is None:
            return None
        current, slot = endpoint
        while True:
            owners[slot] = current
            assigned[current] = slot
            if current == root:
                break
            current, slot = parents[current]
    return {players[index].id: slots[slot] for index, slot in assigned.items()}


def roster_check(players: list[Player], rules: Rules) -> dict:
    if not rules.roster_slots:
        return {"status": "unknown", "reason": "Roster slot configuration is missing."}
    slots = [slot for slot, count in rules.roster_slots.items() for _ in range(count)]
    if len(players) > len(slots):
        return {"status": "infeasible", "reason": "Roster exceeds total configured capacity."}
    assignment = match(players, slots)
    if assignment is not None:
        return {
            "status": "feasible",
            "assignment": assignment,
            "reason": "Players fit configured slots using imported eligibility. This is not a daily lineup or transaction authorization.",
        }
    if match(players, slots, optimistic=True) is not None:
        return {
            "status": "unknown",
            "reason": "Missing position or injury-slot eligibility prevents confirming roster fit.",
        }
    return {
        "status": "infeasible",
        "reason": "Players cannot fit configured positions, bench and eligible injury slots.",
    }


def acquisition_check(team: Team, rules: Rules, now: datetime | None = None) -> dict:
    limit = rules.weekly_acquisition_limit
    if limit is None:
        return {"status": "unknown", "reason": "Weekly acquisition limit is not configured."}
    if limit == 0:
        return {
            "status": "infeasible",
            "remaining": 0,
            "reason": "Configured acquisition limit is zero.",
        }
    usage = team.acquisitions
    now = now or datetime.now(timezone.utc)
    if usage is None or not usage.period_start <= now < usage.period_end:
        return {
            "status": "unknown",
            "reason": "Acquisition usage for the current period is missing or expired.",
        }
    remaining = max(0, limit - usage.used)
    return {
        "status": "feasible" if remaining else "infeasible",
        "remaining": remaining,
        "reason": "Based on imported period usage; pending or later transactions are not known.",
    }
