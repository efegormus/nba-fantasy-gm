"""Combine tool evidence without pretending independently scored moves form one legal plan."""


def decision_review(observations: dict) -> dict:
    next_checks, alternatives, seen = [], [], set()
    for tool in ("waiver_scout", "trade_analyzer"):
        result = observations.get(tool, {})
        if result.get("status") == "blocked":
            reason = result.get("reason", "Resolve missing input before evaluating moves.")
            if reason not in seen:
                seen.add(reason)
                next_checks.append(
                    {"action": "RESOLVE_INPUT", "reason": reason, "source_tool": tool}
                )
        for index, candidate in enumerate(result.get("candidates", [])):
            if tool == "waiver_scout":
                move_id = f"waiver-{index + 1}"
                players = [candidate["add"], candidate["drop"]]
                summary = f"Add {candidate['add_name']}; drop {candidate['drop_name']}"
            else:
                move_id = f"trade-{index + 1}"
                players = [candidate["offer"], candidate["request"]]
                summary = f"Offer {candidate['offer_name']}; request {candidate['request_name']}"
            alternatives.append(
                {
                    "id": move_id,
                    "source_tool": tool,
                    "candidate_index": index,
                    "summary": summary,
                    "player_ids": players,
                    "conflicts_with": [],
                    "news_evidence_ids": [],
                    "provisional": True,
                }
            )
    news = observations.get("news_monitor", {})
    for follow_up in news.get("actions", []):
        next_checks.append(
            {
                "action": follow_up["action"],
                "player_id": follow_up["player_id"],
                "reason": follow_up["instruction"],
                "source_tool": "news_monitor",
                "evidence_ids": follow_up["evidence_ids"],
            }
        )
    for withheld in news.get("withheld", []):
        next_checks.append(
            {
                "action": "VERIFY_NEWS",
                "player_id": withheld["player_id"],
                "reason": withheld["reason"],
                "source_tool": "news_monitor",
                "evidence_ids": withheld["evidence_ids"],
            }
        )
    for index, left in enumerate(alternatives):
        left["news_evidence_ids"] = [
            event["id"]
            for event in news.get("events", [])
            if event["player_id"] in left["player_ids"]
        ]
        for right in alternatives[index + 1 :]:
            if set(left["player_ids"]) & set(right["player_ids"]):
                left["conflicts_with"].append(right["id"])
                right["conflicts_with"].append(left["id"])
    return {
        "next_checks": next_checks,
        "alternatives": alternatives,
        "notice": "Each alternative was evaluated separately. Shared-player alternatives conflict. Even alternatives without a listed conflict must be re-evaluated together before acting. News references may be unverified, stale or contradictory; inspect the source evidence. No combined plan or transaction authorization is implied.",
    }
