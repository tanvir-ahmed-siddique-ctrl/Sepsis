"""Silent-pilot, connector, governance and writer-lease tables.

Revision ID: 20261016_0002
Revises: 20260930_0001
"""

from alembic import op

from app.records import metadata

revision = "20261016_0002"
down_revision = "20260930_0001"
branch_labels = None
depends_on = None

TABLES = (
    "site_config",
    "writer_lease",
    "prediction_records",
    "feedback_records",
    "outcome_records",
    "connector_events",
    "ingest_requests",
    "connector_spool",
    "bed_ownership",
    "handoff_notes",
    "local_protocols",
    "export_log",
)


def upgrade() -> None:
    bind = op.get_bind()
    for name in TABLES:
        metadata.tables[name].create(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for name in reversed(TABLES):
        metadata.tables[name].drop(bind, checkfirst=True)
