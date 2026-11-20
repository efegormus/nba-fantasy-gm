from app.decision_review import decision_review


def waiver(add="free", drop="mine"):
    return {"add": add, "drop": drop, "add_name": add, "drop_name": drop}


def trade(offer="mine", request="theirs"):
    return {"offer": offer, "request": request, "offer_name": offer, "request_name": request}


def test_cross_tool_shared_player_conflicts_are_symmetric():
    result = decision_review(
        {
            "waiver_scout": {"candidates": [waiver(), waiver("other", "mine2")]},
            "trade_analyzer": {"candidates": [trade()]},
        }
    )
    rows = {r["id"]: r for r in result["alternatives"]}
    assert rows["waiver-1"]["conflicts_with"] == ["trade-1"]
    assert rows["trade-1"]["conflicts_with"] == ["waiver-1"]
    assert rows["waiver-2"]["conflicts_with"] == []
    assert all(r["provisional"] for r in rows.values())


def test_duplicate_blockers_are_condensed_and_news_evidence_is_not_promoted():
    result = decision_review(
        {
            "waiver_scout": {"status": "blocked", "reason": "Import data", "candidates": []},
            "trade_analyzer": {"status": "blocked", "reason": "Import data", "candidates": []},
            "news_monitor": {
                "withheld": [{"player_id": "p", "evidence_ids": ["report"], "reason": "Unverified"}]
            },
        }
    )
    assert len(result["next_checks"]) == 2
    assert result["next_checks"][1]["action"] == "VERIFY_NEWS"
    assert result["alternatives"] == []


def test_relevant_news_links_include_unverified_reports_for_review_only():
    result = decision_review(
        {
            "waiver_scout": {"candidates": [waiver()]},
            "news_monitor": {
                "events": [
                    {"id": "news", "player_id": "free", "verification": "unverified"},
                    {"id": "unrelated", "player_id": "x"},
                ]
            },
        }
    )
    assert result["alternatives"][0]["news_evidence_ids"] == ["news"]
    assert result["next_checks"] == []
    assert "unverified" in result["notice"]


def test_news_followups_carry_exact_evidence_references():
    result = decision_review(
        {
            "news_monitor": {
                "actions": [
                    {
                        "action": "MONITOR_STATUS",
                        "player_id": "p",
                        "instruction": "Recheck before lock",
                        "evidence_ids": ["source1"],
                    }
                ]
            }
        }
    )
    assert result["next_checks"][0]["evidence_ids"] == ["source1"]
    assert result["next_checks"][0]["action"] == "MONITOR_STATUS"
