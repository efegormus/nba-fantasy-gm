# Fantasy NBA GM

A local-first, read-only Fantasy Basketball GM focused on three workflows: waiver opportunities, mutually beneficial trades, and news/injury evidence. **No model training, paid AI API, Yahoo API approval, or browser extension is required.**

The main product is the Streamlit **GM Workspace**, backed by FastAPI and SQLite. It runs deterministic analysis tools by default. An optional, already-installed local Ollama model can select tools through a bounded agent loop. The UI identifies which execution mode was used; the default is not presented as LLM-powered AI.

## Current capabilities

- Yahoo league **210163** is the default target, using Head-to-Head 9 Categories.
- League Setup configures URL, scoring, roster rules, acquisition limits, waiver rules and managed team. Unknown settings stay unknown.
- CSV/JSON import with validation, preview, confirmation and immutable league-scoped snapshots.
- Strict separation of real data and a fully fictional 12-team demo.
- Correct aggregate FG% / FT%, turnover direction and missing-stat handling.
- **Waiver scout:** compares add/drop alternatives using the managed team's three weakest standardized categories.
- **Trade analyzer:** checks one-for-one swaps for positive heuristic value to both teams.
- **News monitor:** turns fresh, explicitly typed, user-verified reports into source-linked lineup/role checks or waiver monitoring. Conflicting, stale or unverified latest reports withhold follow-ups. It does not fetch live news or infer recovery dates.
- **GM workflow:** collects evidence, records tool execution, and displays provisional results. A joint decision review consolidates input/news checks, links relevant reports and flags alternatives sharing players across waiver/trade tools. Reports persist with their original snapshot, goal, selected team, rules and workflow version; review them in **Analysis history**. Optional local tool calling cannot execute transactions or change league data.

Move analysis uses imported statistics, not forecasts or win probabilities. It requires fresh data, a selected team, complete player stats and a declared common `stats_horizon`. It checks roster-slot fit for both trade partners and imported acquisition usage within the declared current period. Impossible rosters and exhausted acquisition limits are excluded; unknown eligibility/rules remain unknown. It does not yet validate schedule locks, pending transactions, waiver priority or trade restrictions. All move ideas are provisional alternatives, not a combined executable plan.

## Setup (macOS / Windows)

Install Python 3.12+. From the repository root:

macOS:

```sh
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python scripts/setup_local.py
```

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python scripts/setup_local.py
```

The setup script creates an ignored `.env` with a random local token and applies the database migration. It does not overwrite existing configuration. If you copied `.env.example` manually, set `LOCAL_API_TOKEN` to at least 32 randomly generated characters.

Start the API:

```sh
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

In another terminal, activate the same environment and launch the dashboard:

```sh
python -m streamlit run dashboard/main.py --server.address 127.0.0.1
```

Open **http://127.0.0.1:8501**. Choose **Demo → Load fictional demo league**, select a team and save. Open **GM Workspace → Run GM analysis**. All demo teams, players and statistics are fictional.

For real data, select **Real league** and import your own authorized data. The URL and ID identify the target; they do not authorize Yahoo access:

```dotenv
YAHOO_LEAGUE_ID=210163
YAHOO_LEAGUE_URL=https://basketball.fantasysports.yahoo.com/nba/210163
```

These environment values initialize the target. Saved dashboard settings take precedence. Changing the real target clears the selected team and roster rules; old snapshots stay partitioned under their original league ID.

## Optional local AI

If you already have Ollama running locally with a tool-capable model installed, configure:

```dotenv
OLLAMA_ENABLED=true
OLLAMA_MODEL=your-installed-model-name
```

Restart the backend and check **Use my configured local Ollama model** in GM Workspace. The application contacts only `127.0.0.1:11434`; it never downloads models. A run is limited to four model rounds, four calls per round, and four allowlisted read-only tools. Invalid calls or connection errors fall back to deterministic analysis.

The model selects tools; all numerical results come from Python calculations. Free-form model prose is not shown as verified advice. Full autonomous planning, learned conversational memory, live monitoring and sophisticated strategy reasoning are future work. Saved run history is an evidence archive, not learned memory. See [agent design](docs/AGENT_WORKFLOW.md).

## Imports and freshness

Use the dashboard's blank templates or paste JSON. Import a complete snapshot containing teams, rostered players, free agents and waiver players. Confirmation replaces the current view and retains older snapshots. JSON supports stats, empty teams and optional news; CSV supports roster/availability rows only.

See [import schema](docs/IMPORTS.md). Effective timestamps must have timezones and cannot be in the future. Uploading old data does not make it fresh. Current freshness thresholds are 24/48 hours; move tools block any data that is not FRESH. Failed imports do not update the last-success timestamp.

Existing installations: run `python scripts/setup_local.py` after pulling updates to apply database migrations without overwriting `.env` or existing imports. Historical reports retain their original evidence and must not be treated as current recommendations.

## Verification

```sh
python -m pytest
```

Tests use fictional fixtures and temporary databases. They cover mode isolation, league changes, validation, authorization, shooting aggregation, tool restrictions, stale/missing inputs and local-model fallback. A live local model is not required for tests.

## Optional legacy sidebar

An early read-only Chrome sidebar remains in `extension/`, but is outside the main product focus. It displays connection metadata and a link to the dashboard. The GM works without it.

To build it with Node 22+:

```sh
npm --prefix extension ci
npm --prefix extension test
npm --prefix extension run build
python scripts/check_extension.py
```

Load `extension/dist` using Chrome's Load unpacked. Its Options page shows the extension origin to add to `.env` `ALLOWED_ORIGINS`; restart the API, then enter your **local API token**, never Yahoo credentials. It requests storage and the loopback backend host only. No Yahoo page data, cookies or credentials are collected.

## Boundaries and next work

No Yahoo credentials, session extraction, DOM scraping, automatic transactions or paid AI APIs. The backend must bind to loopback. Private `.env`, databases and imports are ignored by Git. If the dashboard is offline, check the API process; if authorization fails, check the local token and allowed origins.

The snapshot schema is not yet a normalized historical analytics warehouse. No scheduler, Telegram delivery, live news/NBA feed, matchup simulator or approved Yahoo OAuth integration exists. News follow-ups are source-linked checks and monitoring prompts, not inferred replacements or numerical injury boosts.

See [roadmap](docs/ROADMAP.md), [architecture](docs/ARCHITECTURE.md), and [security notes](docs/SECURITY.md).
