"""add descrizione_ita to shirts

Revision ID: 4c3e5f28a1a7
Revises: d556f7055946
Create Date: 2026-02-03 10:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4c3e5f28a1a7'
down_revision = 'd556f7055946'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('descrizione_ita', sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.drop_column('descrizione_ita')
