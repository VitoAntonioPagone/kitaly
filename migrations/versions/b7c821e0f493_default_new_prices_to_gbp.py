"""Default new public prices to GBP without converting existing prices."""
from alembic import op
import sqlalchemy as sa

revision = 'b7c821e0f493'
down_revision = 'a4e7c901d632'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shirts') as batch_op:
        batch_op.alter_column('price_currency', existing_type=sa.String(3),
                              existing_nullable=False, server_default='GBP')


def downgrade():
    with op.batch_alter_table('shirts') as batch_op:
        batch_op.alter_column('price_currency', existing_type=sa.String(3),
                              existing_nullable=False, server_default='EUR')
