"""Add explicit customer-facing prices without exposing internal valuations."""
from alembic import op
import sqlalchemy as sa

revision = 'a4e7c901d632'
down_revision = '6a9d8f1c2b3e'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shirts') as batch_op:
        batch_op.add_column(sa.Column('public_price', sa.Numeric(10, 2), nullable=True))
        batch_op.add_column(sa.Column('price_currency', sa.String(3), nullable=False, server_default='EUR'))


def downgrade():
    with op.batch_alter_table('shirts') as batch_op:
        batch_op.drop_column('price_currency')
        batch_op.drop_column('public_price')
