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
