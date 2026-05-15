"""Add titles column to users table

Revision ID: 003
Revises: 002
Create Date: 2026-05-14 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('titles', postgresql.ARRAY(sa.Text()), nullable=True)
    )


def downgrade() -> None:
    op.drop_column('users', 'titles')
