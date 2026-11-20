"""Run from repository root: streamlit run dashboard/main.py."""

import json
from datetime import datetime, timezone
import httpx
import streamlit as st
from app.config import get_settings

st.set_page_config(page_title="Fantasy NBA GM", page_icon="🏀", layout="wide")
settings = get_settings()
API = "http://127.0.0.1:8000/api/v1"
st.title("Fantasy NBA GM")
mode = st.sidebar.radio(
    "Data mode",
    ["real", "demo"],
    format_func=lambda m: "Real league" if m == "real" else "Demo · fictional",
)
page = st.sidebar.radio("Workspace", ["League Setup", "My Team", "GM Workspace"])
st.caption(
    "Real league · user-imported data"
    if mode == "real"
    else "DEMO · All teams, players and statistics are fictional"
)


def api(method, path, payload=None):
    try:
        response = httpx.request(
            method,
            API + path,
            params={"mode": mode},
            json=payload,
            headers={"Authorization": "Bearer " + settings.local_api_token},
            timeout=100,
        )
        response.raise_for_status()
        return response.json()
    except httpx.HTTPStatusError as exc:
        st.error(f"Request rejected: {exc.response.text}")
    except httpx.RequestError:
        st.error("Local backend is offline. Start the API using the README instructions.")
    return None


def render_report(report, prefix="current"):
    st.caption(
        f"Engine: {report['engine']} · Data effective: {report['data_effective_at'] or 'Unavailable'}"
    )
    if report["warning"]:
        st.warning(report["warning"])
    st.info(report["summary"])
    review = report.get("decision_review")
    if review:
        st.markdown("#### What to check next")
        for check in review["next_checks"]:
            st.text(f"{check['action'].replace('_', ' ').title()}: {check['reason']}")
        if not review["next_checks"]:
            st.write(
                "No additional input or news checks were flagged by these tools. Move ideas still require manual review."
            )
        if review["alternatives"]:
            st.caption(review["notice"])
            st.dataframe(
                [
                    {
                        "ID": item["id"],
                        "Alternative": item["summary"],
                        "Conflicts with": ", ".join(item["conflicts_with"]) or "None identified",
                        "News to review": ", ".join(item["news_evidence_ids"])
                        or "No imported reports",
                    }
                    for item in review["alternatives"]
                ],
                hide_index=True,
                key=f"{prefix}:decision-review",
            )
    observations = report["observations"]
    for key, title in [
        ("waiver_scout", "Waiver / add-drop"),
        ("trade_analyzer", "Mutually beneficial trades"),
        ("news_monitor", "News and injuries"),
    ]:
        observation = observations.get(key)
        if observation is None:
            continue
        st.markdown(f"#### {title}")
        if observation.get("reason"):
            st.write(observation["reason"])
        if observation.get("risk"):
            st.caption(observation["risk"])
        for index, candidate in enumerate(observation.get("candidates", []), 1):
            with st.expander(f"Alternative {index} · Requires manual review", expanded=index == 1):
                for check_name, check in candidate.get("checks", {}).items():
                    st.caption(
                        f"{check_name.replace('_', ' ').title()}: {check['status']} — {check['reason']}"
                    )
                if key == "waiver_scout":
                    st.text(f"Add {candidate['add_name']} · Drop {candidate['drop_name']}")
                    st.caption(f"Availability at import: {candidate['availability_at_import']}")
                    st.dataframe(
                        [candidate["category_changes"]],
                        hide_index=True,
                        key=f"{prefix}:waiver:{index}",
                    )
                else:
                    st.text(
                        f"Offer {candidate['offer_name']} · Request {candidate['request_name']}"
                    )
                    st.caption(f"Partner team: {candidate['partner_team_id']}")
                    st.dataframe(
                        [
                            {"Team": "Yours", **candidate["your_category_changes"]},
                            {"Team": "Partner", **candidate["partner_category_changes"]},
                        ],
                        hide_index=True,
                        key=f"{prefix}:trade:{index}",
                    )
        if observation.get("rejected_roster_pairs"):
            st.caption(
                f"Excluded {observation['rejected_roster_pairs']} alternatives that cannot fit configured rosters."
            )
        if observation.get("status") == "evaluated" and not observation.get("candidates"):
            st.write("No positive alternatives found by the current heuristic.")
        if observation.get("search_truncated"):
            st.caption("Search limit reached; some alternatives were not evaluated.")
        for index, action in enumerate(observation.get("actions", []), 1):
            st.text(f"{action['action'].replace('_', ' ').title()} · {action['player_name']}")
            st.write(action["instruction"])
            st.caption(
                f"User-verified report · {action['published_at']} · Not independently verified"
            )
            st.link_button(
                "Follow-up evidence", action["source_url"], key=f"{prefix}:action:{index}"
            )
        if observation.get("withheld"):
            with st.expander("Reports needing verification or refresh"):
                st.dataframe(observation["withheld"], hide_index=True, key=f"{prefix}:withheld")
        for event in observation.get("events", []):
            st.text(event["headline"])
            st.caption(
                f"Published: {event['published_at']} · Verification: {event['verification']}"
            )
            st.link_button(
                "View report source", event["source_url"], key=f"{prefix}:news:{event['id']}"
            )
    with st.expander("Analysis steps and calculation details"):
        st.dataframe(report["trace"], hide_index=True, key=f"{prefix}:trace")
        st.json(observations)


status = api("GET", "/league")
if status is None:
    st.stop()
if page == "GM Workspace":
    st.subheader("Fantasy GM · Agent workspace")
    st.write(
        "Inspect your league, compare waiver moves, find mutual trade ideas and review imported news."
    )
    st.caption(
        "Default: deterministic tools. Optional: a locally installed Ollama model selects tools. No model training, paid APIs or automatic transactions."
    )
    question = st.text_area("Your goal", "Review my waiver, trade and news opportunities")
    use_local_ai = st.checkbox("Use my configured local Ollama model", value=False)
    if st.button("Run GM analysis"):
        with st.spinner("Checking league evidence and running read-only tools…"):
            report = api("POST", "/agent/run", {"question": question, "use_local_ai": use_local_ai})
        if report:
            st.success(f"Saved analysis #{report['run_id']}")
            render_report(report)
    st.subheader("Analysis history")
    st.caption(
        "Saved results preserve the original evidence and settings. They are not current recommendations."
    )
    history = api("GET", "/agent/runs")
    runs = history["runs"] if history else []
    if runs:
        labels = {
            row["id"]: f"#{row['id']} · {row['created_at']} · {row['question'][:80]}"
            for row in runs
        }
        selected = st.selectbox(
            "Saved analysis",
            [None, *labels],
            format_func=lambda key: labels.get(key, "Choose a saved analysis"),
            key=f"history:{mode}:{status['league_id']}",
        )
        if selected is not None:
            saved = api("GET", f"/agent/runs/{selected}")
            if saved:
                st.warning(
                    "Historical report: availability, rules and injuries may have changed. Run a new analysis before making decisions."
                )
                render_report(saved["report"], prefix=f"history:{selected}")
                with st.expander("Original evidence and settings"):
                    st.json(
                        {
                            "snapshot_id": saved["snapshot_id"],
                            "context": saved["context"],
                            "evidence": saved["evidence"],
                        }
                    )
                st.download_button(
                    "Download saved report and evidence",
                    json.dumps(saved, indent=2),
                    f"gm-run-{selected}.json",
                    "application/json",
                )
    else:
        st.write("No saved analyses for this league and mode yet.")
    st.stop()

if page == "My Team":
    st.subheader("Imported category totals")
    st.info(
        "Totals use the statistical horizon supplied in your import. They are not live projections."
    )
    if status["setup"]["scoring_format"] != "Head-to-Head 9 Categories":
        st.warning("Category analysis currently supports Head-to-Head 9 Categories only.")
    elif result := api("GET", "/team"):
        st.dataframe([result["totals"]], hide_index=True)
    st.stop()

st.subheader("League Setup")
a, b, c = st.columns(3)
a.metric("Connection", status["connection"].replace("_", " "))
b.metric("Freshness", status["freshness"])
c.metric("Imported teams", status["team_count"] if status["team_count"] is not None else "Unknown")
st.write(
    "Latest successful data refresh:", status["last_successful_refresh"] or "No successful import"
)
st.write("Data effective at:", status["data_effective_at"] or "Unknown")
st.info(
    "Yahoo API is disabled. A league URL does not authorize private data access. Import your own authorized files; no Yahoo login is required."
)
if mode == "demo" and st.button("Load fictional demo league"):
    if api("POST", "/demo"):
        st.rerun()
config = status["setup"]
with st.form("setup"):
    url = st.text_input("Yahoo league URL", config["league_url"])
    formats = ["Head-to-Head 9 Categories", "Head-to-Head Points", "Rotisserie"]
    scoring = st.selectbox("Scoring format", formats, index=formats.index(config["scoring_format"]))
    st.caption(
        "Rules are unknown until configured. Empty acquisition limit means unknown; 0 means no acquisitions."
    )
    slots = st.text_area(
        "Roster slots (JSON)",
        json.dumps(config["rules"]["roster_slots"]),
        help='Example only: {"PG": 1, "UTIL": 2, "BN": 3}',
    )
    limit = st.text_input(
        "Weekly acquisition limit",
        ""
        if config["rules"]["weekly_acquisition_limit"] is None
        else str(config["rules"]["weekly_acquisition_limit"]),
    )
    waivers = st.text_area("Waiver rules", config["rules"]["waiver_settings"] or "")
    team_names = {t["id"]: t["name"] for t in status["teams"]}
    choices = [None, *team_names]
    selected = st.selectbox(
        "My fantasy team",
        choices,
        index=choices.index(config["managed_team_id"])
        if config["managed_team_id"] in choices
        else 0,
        format_func=lambda t: team_names.get(t, "Not selected"),
    )
    if st.form_submit_button("Save league setup"):
        try:
            result = api(
                "PUT",
                "/league",
                {
                    "league_url": url,
                    "scoring_format": scoring,
                    "rules": {
                        "roster_slots": json.loads(slots),
                        "weekly_acquisition_limit": int(limit) if limit.strip() else None,
                        "waiver_settings": waivers or None,
                    },
                    "managed_team_id": selected,
                },
            )
            if result:
                st.rerun()
        except (ValueError, TypeError) as exc:
            st.error(f"Check your roster JSON and acquisition limit: {exc}")

st.subheader("Import rosters, free agents and waiver players")
st.write(
    "Import a complete snapshot. Confirming replaces the current view for this league and mode; older snapshots remain saved. Include all teams and available players together."
)
st.caption(
    "JSON supports statistics and empty teams. CSV supports roster/availability rows; teams are inferred from roster rows. Yahoo may not provide CSV export—use the template or manual JSON entry."
)
metadata = {
    "mode": mode,
    "league_id": status["league_id"],
    "source": "manual" if mode == "real" else "fictional_demo",
    "effective_at": datetime.now(timezone.utc).isoformat(),
}
template = {**metadata, "teams": [], "players": []}
st.download_button(
    "Download blank JSON template",
    json.dumps(template, indent=2),
    "league-template.json",
    "application/json",
)
st.download_button(
    "Download CSV template",
    "id,name,availability,team_id,team_name,positions,yahoo_id,nba_id\n",
    "league-template.csv",
    "text/csv",
)
file = st.file_uploader("Choose JSON or CSV", type=["json", "csv"])
manual = st.text_area("Or paste a complete JSON snapshot", height=160)
effective_key = f"csv_effective:{mode}:{status['league_id']}"
st.session_state.setdefault(effective_key, metadata["effective_at"])
effective = st.text_input(
    "CSV data effective timestamp (ISO 8601 with timezone)", key=effective_key
)
text = file.getvalue().decode("utf-8-sig", errors="replace") if file else manual
fmt = "csv" if file and file.name.lower().endswith(".csv") else "json"
# Preview is tied to the exact input, target and mode; changes invalidate confirmation.
fingerprint = (text, fmt, mode, status["league_id"], effective if fmt == "csv" else "")
if st.button("Validate and preview", disabled=not text.strip()):
    preview = api(
        "POST",
        "/imports/preview",
        {"format": fmt, "text": text, "metadata": {**metadata, "effective_at": effective}},
    )
    st.session_state["preview"] = (fingerprint, preview)
saved = st.session_state.get("preview")
if saved and saved[0] == fingerprint and saved[1]:
    preview = saved[1]
    st.success(f"Validated: {len(preview['teams'])} teams, {len(preview['players'])} players")
    st.json(preview, expanded=False)
    confirmed = st.checkbox(
        "I confirm this data belongs to the selected league and mode and I am authorized to import it."
    )
    if st.button("Confirm import", disabled=not confirmed):
        if api("POST", "/imports", preview):
            del st.session_state["preview"]
            st.rerun()
