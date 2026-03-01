"""add_blinded_signatures_table

Revision ID: f14d959954d2
Revises: 66a7889ab3e3
Create Date: 2026-02-28 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f14d959954d2'
down_revision: Union[str, Sequence[str], None] = '66a7889ab3e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add blinded_signatures table for NUT-09 restore and NUT-13 compatibility."""
    op.create_table(
        'blinded_signatures',
        sa.Column('B_', sa.String(length=66), nullable=False),
        sa.Column('amount', sa.BigInteger(), nullable=False),
        sa.Column('keyset_id', sa.String(length=16), nullable=False),
        sa.Column('C_', sa.String(length=66), nullable=False),
        sa.Column('dleq_e', sa.String(length=64), nullable=True),
        sa.Column('dleq_s', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('B_'),
    )


def downgrade() -> None:
    """Remove blinded_signatures table."""
    op.drop_table('blinded_signatures')
