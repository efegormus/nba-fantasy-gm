"""Evidence-linked follow-up actions from typed reports, never headline inference."""

from datetime import datetime, timezone
from .schemas import Snapshot

HEALTH = {"PLAYER_OUT", "PLAYER_QUESTIONABLE", "PLAYER_RETURN"}
ROLES = {"ROLE_INCREASE", "ROLE_DECREASE"}


def news_review(snapshot: Snapshot | None, managed_team_id, freshness, now=None):
    if snapshot is None:
        return {
            "status": "unavailable",
            "events": [],
            "actions": [],
            "reason": "No league snapshot imported.",
        }
    now = now or datetime.now(timezone.utc)
    players = {p.id: p for p in snapshot.players}
    events, groups, actions, withheld = [], {}, [], []
    for event in snapshot.news:
        age = (now - event.published_at).total_seconds()
        events.append(
            {
                **event.model_dump(mode="json"),
                "freshness_at_run": "FRESH" if 0 <= age < 86400 else "STALE",
            }
        )
        kind = (
            "health"
            if event.event_type in HEALTH
            else "role"
            if event.event_type in ROLES
            else None
        )
        if kind:
            groups.setdefault((event.player_id, kind), []).append(event)
    for (player_id, _), reports in groups.items():
        published = max(event.published_at for event in reports)
        latest = [event for event in reports if event.published_at == published]
        reason = None
        if freshness != "FRESH":
            reason = "League snapshot is not fresh. Refresh ownership and availability first."
        elif len({event.event_type for event in latest}) > 1:
            reason = "Latest reports conflict; verify status before acting."
        elif not any(event.verification == "user_verified" for event in latest):
            reason = "Latest report is unverified; older verified reports are not substituted."
        elif not 0 <= (now - published).total_seconds() < 86400:
            reason = "Latest report is stale or future-dated."
        elif not managed_team_id:
            reason = "Select your fantasy team before personalizing news."
        if reason:
            withheld.append(
                {
                    "player_id": player_id,
                    "evidence_ids": [event.id for event in latest],
                    "reason": reason,
                }
            )
            continue
        event = next(event for event in latest if event.verification == "user_verified")
        player = players[player_id]
        own = player.team_id == managed_team_id
        available = player.availability in {"free_agent", "waiver"}
        action, instruction = None, None
        if own and event.event_type == "PLAYER_OUT":
            action, instruction = (
                "REVIEW_LINEUP",
                "Check your active lineup and eligible injury slots; do not infer a replacement or recovery date.",
            )
        elif own and event.event_type == "PLAYER_QUESTIONABLE":
            action, instruction = (
                "MONITOR_STATUS",
                "Recheck this player's status before lineup lock. Questionable does not mean out.",
            )
        elif own and event.event_type == "PLAYER_RETURN":
            action, instruction = (
                "REVIEW_LINEUP",
                "Review the reported return before activating; minutes and restrictions remain unknown.",
            )
        elif own and event.event_type in ROLES:
            action, instruction = (
                "REVIEW_ROLE",
                "Review this reported role change against current statistics; its numerical fantasy impact is not established.",
            )
        elif available and event.event_type in {"ROLE_INCREASE", "PLAYER_RETURN"}:
            action, instruction = (
                "MONITOR_WAIVER",
                "Investigate this available player's reported change; compare category fit before considering an add.",
            )
        if action:
            actions.append(
                {
                    "action": action,
                    "player_id": player.id,
                    "player_name": player.name,
                    "event_type": event.event_type,
                    "instruction": instruction,
                    "evidence_ids": [event.id],
                    "source_url": str(event.source_url),
                    "published_at": event.published_at.isoformat(),
                    "provisional": True,
                    "verification": "user_verified",
                    "availability_at_import": player.availability,
                }
            )
    return {
        "status": "imported_reports" if events else "unavailable",
        "events": events,
        "actions": actions,
        "withheld": withheld,
        "reason": "User-imported reports only, not independently verified. Follow-ups use explicit event types, not inferred headlines. No live news feed, numerical injury boost or recovery prediction.",
    }
