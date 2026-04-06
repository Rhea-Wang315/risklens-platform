"""add triage fields to decisions

Revision ID: 8f3b2b9c1d4e
Revises: b2f55e300e27
Create Date: 2026-04-06 11:20:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "8f3b2b9c1d4e"
down_revision: Union[str, Sequence[str], None] = "b2f55e300e27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "decisions",
        sa.Column("decision_status", sa.String(length=20), nullable=False, server_default="OPEN"),
    )
    op.add_column("decisions", sa.Column("triage_assignee", sa.String(length=255), nullable=True))
    op.add_column("decisions", sa.Column("triage_notes", sa.Text(), nullable=True))
    op.add_column(
        "decisions",
        sa.Column(
            "triage_updated_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_index(
        op.f("ix_decisions_decision_status"), "decisions", ["decision_status"], unique=False
    )
    op.create_index(
        op.f("ix_decisions_triage_assignee"), "decisions", ["triage_assignee"], unique=False
    )
    op.create_index(
        op.f("ix_decisions_triage_updated_at"), "decisions", ["triage_updated_at"], unique=False
    )
    op.create_index(
        "idx_decision_status_updated",
        "decisions",
        ["decision_status", "triage_updated_at"],
        unique=False,
    )

    op.alter_column("decisions", "decision_status", server_default=None)
    op.alter_column("decisions", "triage_updated_at", server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_decision_status_updated", table_name="decisions")
    op.drop_index(op.f("ix_decisions_triage_updated_at"), table_name="decisions")
    op.drop_index(op.f("ix_decisions_triage_assignee"), table_name="decisions")
    op.drop_index(op.f("ix_decisions_decision_status"), table_name="decisions")

    op.drop_column("decisions", "triage_updated_at")
    op.drop_column("decisions", "triage_notes")
    op.drop_column("decisions", "triage_assignee")
    op.drop_column("decisions", "decision_status")
