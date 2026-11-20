"""Immutable execution reports scoped to the league and evidence used at execution time."""

from datetime import timezone
from sqlalchemy import select
from .storage import AgentRun, ImportSnapshot

WORKFLOW_VERSION = "gm-tools-v1"


class RunHistory:
    def __init__(self, sessions):
        self.sessions = sessions

    def save(self, scope, snapshot, status, question, report):
        if snapshot and snapshot.scope != scope:
            raise ValueError("Run evidence belongs to a different league")
        row = AgentRun(
            scope=scope,
            snapshot_id=snapshot.id if snapshot else None,
            question=question,
            context={
                "setup": status["setup"],
                "freshness_at_run": status["freshness"],
                "workflow_version": WORKFLOW_VERSION,
            },
            report=report,
        )
        with self.sessions.begin() as session:
            session.add(row)
        return row

    @staticmethod
    def summary(row):
        return {
            "id": row.id,
            "snapshot_id": row.snapshot_id,
            "created_at": row.created_at.replace(tzinfo=timezone.utc).isoformat(),
            "question": row.question,
            "engine": row.report["engine"],
            "mode": row.report["mode"],
            "league_id": row.report["league_id"],
            "data_effective_at": row.report["data_effective_at"],
            "managed_team_id": row.context["setup"]["managed_team_id"],
        }

    def list(self, scope, limit=20):
        with self.sessions() as session:
            rows = session.scalars(
                select(AgentRun)
                .where(AgentRun.scope == scope)
                .order_by(AgentRun.id.desc())
                .limit(limit)
            )
            return [self.summary(row) for row in rows]

    def detail(self, scope, run_id):
        with self.sessions() as session:
            row = session.scalar(
                select(AgentRun).where(AgentRun.scope == scope, AgentRun.id == run_id)
            )
            if row is None:
                return None
            snapshot = session.get(ImportSnapshot, row.snapshot_id) if row.snapshot_id else None
            if snapshot and snapshot.scope != scope:
                raise ValueError("Stored evidence scope does not match the run")
            return {
                **self.summary(row),
                "context": row.context,
                "report": row.report,
                "evidence": snapshot.data if snapshot else None,
                "historical": True,
            }
