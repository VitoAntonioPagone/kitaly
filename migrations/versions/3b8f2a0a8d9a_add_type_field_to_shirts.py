"""add type field to shirts

Revision ID: 3b8f2a0a8d9a
Revises: d556f7055946
Create Date: 2026-02-03 12:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3b8f2a0a8d9a'
down_revision = 'd556f7055946'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('type', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.drop_column('type')
