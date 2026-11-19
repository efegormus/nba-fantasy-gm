"""Initial configuration and immutable league snapshots."""

from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "configuration",
        sa.Column("scope", sa.String(), primary_key=True),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_table(
        "import_snapshot",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope", sa.String(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
    )
    op.create_index("ix_import_snapshot_scope", "import_snapshot", ["scope"])


def downgrade():
    op.drop_table("import_snapshot")
    op.drop_table("configuration")
