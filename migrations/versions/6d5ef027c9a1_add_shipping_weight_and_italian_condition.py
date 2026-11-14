"""Add shipping weight and Italian condition notes.

Revision ID: 6d5ef027c9a1
Revises: b83f5d21c901
"""
from alembic import op
import sqlalchemy as sa

revision = '6d5ef027c9a1'
down_revision = 'b83f5d21c901'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('shirts', sa.Column('shipping_weight_grams', sa.Integer(), nullable=True))
    op.add_column('shirts', sa.Column('condition_notes_ita', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('shirts', 'condition_notes_ita')
    op.drop_column('shirts', 'shipping_weight_grams')
