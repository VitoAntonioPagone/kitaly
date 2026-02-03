"""make tipologia nullable

Revision ID: 9a2b6c1d0f4a
Revises: 7e2b1f6c8a41
Create Date: 2026-02-03 12:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a2b6c1d0f4a'
down_revision = '7e2b1f6c8a41'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.alter_column('tipologia', existing_type=sa.String(length=50), nullable=True)


def downgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.alter_column('tipologia', existing_type=sa.String(length=50), nullable=False)
