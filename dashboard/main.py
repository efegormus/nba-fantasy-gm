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
            st.caption(
                f"Engine: {report['engine']} · Data effective: {report['data_effective_at'] or 'Unavailable'}"
            )
            if report["warning"]:
                st.warning(report["warning"])
            st.info(report["summary"])
            st.dataframe(report["trace"], hide_index=True)
            for name, observation in report["observations"].items():
                with st.expander(name.replace("_", " ").title(), expanded=True):
                    st.json(observation)
            st.download_button(
                "Download GM report",
                json.dumps(report, indent=2),
                "gm-report.json",
                "application/json",
            )
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
