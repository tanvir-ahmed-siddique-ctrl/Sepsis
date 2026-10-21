"""Local accounts, care units, encounters and NEWS2 records.

Revision ID: 20261016_0003
Revises: 20261016_0002
"""

from alembic import op

from app.records import metadata

revision = "20261016_0003"
down_revision = "20261016_0002"
branch_labels = None
depends_on = None

TABLES = ("site_users", "revoked_tokens", "care_units", "encounters", "news2_records")


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        metadata.tables[name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        metadata.tables[name].drop(bind, checkfirst=True)
