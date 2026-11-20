# Roadmap

## Product focus

A personal agentic Fantasy GM built around waiver/add-drop analysis, mutually beneficial trade analysis, and news/injury evidence. No ML training project. A browser extension is optional and outside the core roadmap.

## Implemented

- Local configuration, SQLite snapshots and migration
- Default Yahoo league 210163 and configurable league setup
- Real/demo isolation, manual import preview/validation/confirmation
- Nine-category descriptive totals
- Read-only GM tools: provisional add/drop comparison, one-for-one mutual trade heuristic, imported-news evidence
- Bounded optional Ollama tool-selection loop with deterministic fallback
- GM Workspace with readable move alternatives, execution trace and report download
- Durable analysis history preserving original snapshot, settings, goal and workflow version, isolated by league/mode

## Next

1. The user confirmed the three guiding principles: waiver/add-drop, mutually beneficial trades, and news/injury analysis. Refine their evaluation quality.
2. Import richer authorized statistics and schedules with explicit provenance and statistical horizons.
3. Validate roster positions, acquisition usage, trade restrictions and waiver rules before judging move legality.
4. Add verified news refresh and evidence-based injury opportunity analysis.
5. Improve strategy customization, punt choices, conflict resolution and trade candidate quality.
6. Build reviewable multi-step plans and scoped conversational memory on the persisted run/evidence archive.
7. Evaluate a locally installed tool-capable model on real user goals; improve planning without letting models invent numerical evidence.
8. Add optional scheduling and deduplicated notifications only after decision quality is validated.

## Not claimed

The current optional local model integration is a bounded tool selector, not a fully autonomous GM. Current heuristics use descriptive input stats, not predictions or matchup win probabilities. No live-news connection or end-to-end local-model run has been verified. Yahoo transactions remain manual.
