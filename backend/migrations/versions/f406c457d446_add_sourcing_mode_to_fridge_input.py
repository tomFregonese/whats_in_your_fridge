"""add sourcing mode to fridge input

Revision ID: f406c457d446
Revises: e30464db9bc8
Create Date: 2026-09-12 18:53:11.222852

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = 'f406c457d446'
down_revision: Union[str, Sequence[str], None] = 'e30464db9bc8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # `sourcing_mode` needs a server default so `ADD COLUMN ... NOT NULL`
    # doesn't fail against a SQLite file with existing `fridge_input` rows
    # — same reasoning as `ffd7922d8ec7`/`e30464db9bc8`. Pre-existing
    # submissions predate this constraint and already behaved like
    # `fridge_plus_shopping` (see `SourcingMode`'s docstring), so that's
    # the backfill value.
    op.add_column(
        'fridge_input',
        sa.Column(
            'sourcing_mode',
            sqlmodel.sql.sqltypes.AutoString(),
            nullable=False,
            server_default='fridge_plus_shopping',
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('fridge_input', 'sourcing_mode')
