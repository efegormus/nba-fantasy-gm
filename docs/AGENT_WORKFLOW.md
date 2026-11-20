# Fantasy GM agent workflow

The workflow operates on the selected league and mode. Its four read-only tools inspect setup/freshness, compare waiver alternatives, evaluate mutually beneficial one-for-one trades, and present imported news evidence. No tool changes Yahoo or local league configuration.

By default a deterministic coordinator executes all four checks. This is explicitly labeled as a workflow, not LLM AI. If the user enables a locally installed Ollama model, a bounded tool-calling loop can choose tool order and inspect results. Missing checks are completed deterministically. Only zero-argument allowlisted tools are accepted; the model cannot select a different league or mode. Repeated calls reuse results. Invalid calls trigger a safe fallback.

The [official Ollama tool-calling protocol](https://docs.ollama.com/capabilities/tool-calling) supplies assistant tool calls and tool-result messages over `/api/chat`. We use the local HTTP endpoint, no paid SDK, no cloud host and no automatic model download. Tests mock the protocol; a real installed model is still required to verify inference end to end.

## Numerical methods

For each imported team, aggregate all nine categories, including volume-weighted FG% and FT%. Across those team totals, compute each category's population mean and standard deviation. Categories with no variation or undefined percentages are excluded. Reverse the sign for turnovers. Each team's three lowest standardized categories define its current heuristic needs.

For an add/drop pair, recalculate the managed roster and sum category deltas divided by the corresponding population standard deviations over those needs. Positive values become provisional candidates. For a trade, perform the same calculation independently for both teams; retain only swaps with positive gains on both sides. This score is a ranking heuristic, not a probability, projection or guarantee. Team size, punts and accumulated statistical horizons can materially change its usefulness.

The waiver search is capped at 400 available players and 100 managed roster players; trade search at 10,000 pairs. Reports disclose truncation. The top five alternatives are returned, with exact category deltas and risks. The user must compare alternatives rather than execute them all.

## Evidence and limits

Move tools block missing/stale/aging data, unsupported scoring, missing team selection, missing stats or missing shared statistical horizon. A configured zero acquisition limit blocks adds. Roster-slot fit uses maximum bipartite matching against configured positions, bench and explicitly eligible injury slots. An optimistic matching pass distinguishes unknown eligibility from proven impossibility. Both trade partners are checked. Acquisition usage must have an explicit current period; expired/missing counts remain unknown. Candidates that fail known checks are removed; every retained candidate remains provisional because locks, pending transactions and trade/waiver restrictions are not fully known.

News reports require a player reference, URL and publication timestamp. User-marked verification is not independent verification. The workflow does not infer playing-time changes, recovery dates or current availability from a headline. Explicit typed reports can produce lineup reviews, status/role checks and waiver monitoring. The latest report per player and health/role channel is used; contradictory same-time reports, stale reports and a newer unverified report suppress follow-ups. Reports cannot postdate their snapshot. User-verified is never presented as independently verified.

Only tool-generated structured results are displayed. Model-generated prose is not promoted into facts or recommendations. Successful workflow executions (including blocked-data reports and model fallbacks) are saved with their original snapshot reference, goal, setup, freshness-at-run and workflow version. History endpoints restrict both listing and direct ID lookup to the selected league/mode. New imports never rewrite old evidence. No-data reports explicitly preserve a null snapshot. Historical reports are labeled historical; their original freshness is not a claim of current freshness. Unexpected execution failures are not yet archived. Conversational memory, live monitoring and richer adaptive planning remain future work.
