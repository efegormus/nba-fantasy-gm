# Local security and data boundaries

No Yahoo API is enabled. The system never collects Yahoo account passwords, browser cookies or session tokens. The optional sidebar observes its page URL solely to match a league; it does not harvest page content or modify Yahoo forms.

Local API pairing uses a randomly generated token stored in ignored `.env` and extension-owned storage. Only trusted extension contexts can access that storage. The background worker does not return the token to the content script. Reset the local token if it is exposed.

The API must bind to 127.0.0.1. Origin allowlisting supplements bearer authentication. Do not configure wildcard origins or expose ports through public tunnels. The dashboard is a local trusted interface without multi-user authorization.

Private snapshots live in ignored SQLite files. Real imports and analysis outputs belong under `data/imports/`, also ignored. Demo artifacts may be committed only when clearly fictional. The app accepts JSON/CSV data, never serialized Python model objects from users.

Future Yahoo API support requires confirmed API entitlement and secure user-initiated OAuth. No OAuth flow is currently implemented. No automated fantasy transactions will be added.

Development dependency audit (2026-11-18): the latest installed Vite 8.3.8 / Vitest 5.1.1 still inherit an npm advisory for picomatch 4.0.7 (ReDoS with crafted glob patterns). The registry's latest picomatch was 4.0.7, so no patched version was available during setup. This affects development glob tooling, not a Yahoo data integration; do not expose development/test servers to untrusted clients. Re-run `npm audit` when updating dependencies. Earlier critical Vitest/tinypool findings were removed by upgrading.

The optional local Ollama workflow accepts only four read-only tool names, no tool arguments, at most four planning rounds, and at most four calls per round. Calls are deduplicated. The model cannot choose a league, change configuration, browse, run a shell or transact. Arbitrary model prose is not displayed as verified advice. Local inference contacts only 127.0.0.1:11434 and does not download models.
