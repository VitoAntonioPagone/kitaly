"""add sold and internal price to shirts

Revision ID: 1f4c9d3b8a2e
Revises: b1f302b9d5c1
Create Date: 2026-03-05 15:05:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1f4c9d3b8a2e'
down_revision = 'b1f302b9d5c1'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shirts', sa.Column('sold', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('shirts', sa.Column('internal_price', sa.Numeric(10, 2), nullable=True))


def downgrade():
    op.drop_column('shirts', 'internal_price')
    op.drop_column('shirts', 'sold')
