"""Create restart state and append-only audit tables.

Revision ID: 20260930_0001
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision = "20260930_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "engine_state",
        sa.Column("state_key", sa.String(length=64), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.Column("updated_at", sa.String(length=64), nullable=False),
    )
    op.create_table(
        "audit_events",
        sa.Column("audit_id", sa.String(length=64), primary_key=True),
        sa.Column("ordinal", sa.BigInteger(), nullable=False, unique=True),
        sa.Column("event_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("previous_hash", sa.String(length=64), nullable=False),
        sa.Column("recorded_at", sa.String(length=64), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("engine_state")
