# Manual import contract

Use only data you are authorized to access. Yahoo does not necessarily offer export on every page. The application does not retrieve private league information from a URL.

A JSON snapshot has:

- `mode`: `real` or `demo`
- `league_id`: the configured real ID, or `demo`
- `source`: `manual` for real data, `fictional_demo` for demo
- `effective_at`: actual data timestamp with timezone, not a future timestamp
- `teams`: objects with stable string `id` and `name`
- `players`: objects with stable string `id`, `name`, `availability`, optional `team_id`, `positions`, `yahoo_id`, `nba_id`, and `stats`

Availability is `rostered`, `free_agent` or `waiver`. Only rostered players have `team_id`; it must reference an imported team. IDs must be unique. Display names need not be unique. Team ownership is selected manually in League Setup.

Optional stats fields: `pts,reb,ast,stl,blk,threes,fgm,fga,ftm,fta,turnovers`. Supply all values for a consistent statistical horizon. All fields are required in a supplied stats object; omit the entire stats object when statistics are unknown. Statistics cannot be negative or nonfinite; makes cannot exceed attempts. Team percentages use total makes / total attempts. Category totals are descriptive and not projections.

CSV header:

```csv
id,name,availability,team_id,team_name,positions,yahoo_id,nba_id
```

Separate multiple positions with `|`. Leave team columns empty for free agents and waiver players. CSV does not support stats or teams with no roster rows; use JSON for those cases. Supply the CSV effective timestamp in the dashboard. Fixed column names are required; arbitrary external column mapping is not implemented.

Imports are full snapshots, not partial merges. If you import only free agents, you will replace the roster view too. Combine all rows into one snapshot first. Use preview to verify counts and content before confirming. Blank templates intentionally contain no fabricated teams or players and need filling before validation.

Rules are configured separately in League Setup. Unknown limits are null, while zero means no acquisitions. The roster-slot dictionary accepts PG, SG, G, SF, PF, F, C, UTIL, BN, IL and IL+. Waiver settings are currently free text, not machine-enforced transaction rules.

For move analysis, declare `stats_horizon` describing the common statistical horizon for every player. Do not mix season totals and per-game averages. Optional `news` contains objects with `id`, `player_id`, `headline`, `source_url`, timezone-aware `published_at`, and `verification` (`unverified` or `user_verified`). User verification is not independent verification by the application. News must reference an imported player; a source URL is stored as evidence and is not fetched.

## Roster and acquisition evidence

`positions` accepts PG, SG, SF, PF, C, G, F or UTIL. An empty list means unknown eligibility. Optional player `injury_slots_eligible` is null when unknown, `[]` when neither injury slot is eligible, or an explicit list of `IL` / `IL+`. Eligibility for one does not automatically imply eligibility for the other. Report the eligibility supplied by your league; do not infer it from a news headline.

Each team can include `acquisitions`: an object with nonnegative `used` and timezone-aware `period_start` / `period_end`. The period is start-inclusive and end-exclusive and must contain the snapshot's effective timestamp. The workflow only uses counts while that explicit period is current; it does not assume a reset day or automatically reset usage. A missing object is unknown, not zero. Import counts in a full JSON snapshot; CSV does not carry them.

Optional news `event_type` values are OTHER (default), PLAYER_OUT, PLAYER_QUESTIONABLE, PLAYER_RETURN, ROLE_INCREASE, ROLE_DECREASE. Types must be entered explicitly; headlines are not parsed into facts. Publication timestamps cannot exceed the snapshot effective timestamp. Only current user-verified typed reports yield personalized follow-up checks, not automatically executable moves.
