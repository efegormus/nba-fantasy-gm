# Architecture

The backend is a modular monolith: validated schemas, configuration, providers, league service, snapshot storage, descriptive analytics and a bounded read-only GM workflow. Alembic owns schema creation. Streamlit calls the authenticated loopback REST API for league data. Its GM Workspace displays structured tool results and an execution trace.

`configuration` stores separate demo and real setup documents. `import_snapshot` stores immutable validated snapshots under `demo` or `real:<league_id>`. Current views use the newest successful snapshot for the requested scope. Switching leagues clears selected team and rules; data is never copied between scopes. Import provenance and league ID are validated before writes.

The original raw upload bytes are not retained; the validated normalized document is preserved. Fully normalized player/game/roster tables and raw-file provenance belong to the next data warehouse migration.

API routes:

- `GET /health`: public minimal health status
- `GET/PUT /api/v1/league?mode=real|demo`: status / setup
- `POST /api/v1/imports/preview`: validate CSV/JSON without mutation
- `POST /api/v1/imports`: commit a validated snapshot
- `POST /api/v1/demo`: generate only the fictional demo scope
- `GET /api/v1/team`: selected team's descriptive category totals
- `POST /api/v1/agent/run`: run and persist the bounded read-only GM workflow
- `GET /api/v1/agent/runs?mode=real|demo&limit=20`: newest saved reports, bounded to 100
- `GET /api/v1/agent/runs/{id}?mode=real|demo`: historical report and its original evidence, with scoped lookup
- `GET /api/v1/recommendations`: compatibility empty state directing users to GM Workspace

All data endpoints require a random local bearer token. Origin headers, when present, must match an explicit allowlist. No wildcard CORS. The Chrome background worker alone holds the local pairing token; content messages have constrained sender and payload checks. The sidebar receives connection metadata, not private rosters or tokens. React escapes displayed text and Shadow DOM isolates styling.

No Yahoo network calls, private API interception, session access or account mutations are implemented. An approved future provider must use user-initiated secure OAuth and permitted read-only scopes. OAuth approval alone must not be assumed to grant API entitlement.

Migration 0002 adds `agent_run`. Each record preserves the original question, report, setup, workflow version and nullable foreign key to an immutable import snapshot. The execution scope is captured before inference, so a later configuration change cannot reassign a report to another league. History is append-only through the API. Listing returns summaries; detail includes private evidence and requires the same local authorization.
