# Repository conventions

This is a local-first Python modular monolith with a Streamlit dashboard and an optional read-only Chrome extension.

- Keep real data partitioned by league ID and separate from fictional demo data.
- The default Yahoo league is 210163. Its URL does not grant private data access.
- Never infer team count, ownership, roster rules, acquisition limits or waivers.
- No Yahoo credential collection, session extraction, DOM scraping, transaction automation or paid AI APIs.
- Keep the Yahoo provider disabled until an approved, user-initiated OAuth integration is implemented.
- Use validated schemas, immutable import snapshots, timezone-aware timestamps and SQLite migrations.
- Use player IDs, not names, for identity. Reject duplicates and invalid ownership.
- Missing input must remain missing, never be replaced by fictional statistics.
- Focus on evidence-grounded agent workflows for waiver, trade, and news/injury analysis. No ML training pipeline. Treat model output as untrusted; calculations and permissions belong to deterministic tools.
- Run `python -m pytest`, and `npm --prefix extension test` / `npm --prefix extension run build` for relevant changes.
- Do not commit .env, databases, user imports, tokens or node_modules.
- Prefer focused branches and commits. Push when authorized by the user. Never force push without explicit permission.
- Update README and docs/ROADMAP.md with implemented behavior and remaining limitations.
