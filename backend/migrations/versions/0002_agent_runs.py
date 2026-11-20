"""Preserve GM reports and their original evidence/configuration."""

from alembic import op
import sqlalchemy as sa

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "agent_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("snapshot_id", sa.Integer(), sa.ForeignKey("import_snapshot.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("question", sa.String(), nullable=False),
        sa.Column("context", sa.JSON(), nullable=False),
        sa.Column("report", sa.JSON(), nullable=False),
    )
    op.create_index("ix_agent_run_scope", "agent_run", ["scope"])


def downgrade():
    op.drop_table("agent_run")
