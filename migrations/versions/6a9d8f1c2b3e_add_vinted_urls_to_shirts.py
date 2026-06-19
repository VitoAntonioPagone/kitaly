"""add Vinted URLs to shirts

Revision ID: 6a9d8f1c2b3e
Revises: 1f4c9d3b8a2e
Create Date: 2026-06-19
"""

from alembic import op
import sqlalchemy as sa


revision = '6a9d8f1c2b3e'
down_revision = '1f4c9d3b8a2e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('vinted_uk_url', sa.String(length=2048), nullable=True))
        batch_op.add_column(sa.Column('vinted_eu_url', sa.String(length=2048), nullable=True))


def downgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.drop_column('vinted_eu_url')
        batch_op.drop_column('vinted_uk_url')
