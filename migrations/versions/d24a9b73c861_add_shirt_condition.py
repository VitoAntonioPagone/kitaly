"""Add optional condition scores and notes to individual shirts."""
from alembic import op
import sqlalchemy as sa

revision = 'd24a9b73c861'
down_revision = 'b7c821e0f493'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('shirts') as batch_op:
        batch_op.add_column(sa.Column('condition_rating', sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column('condition_notes', sa.Text(), nullable=True))
        batch_op.create_check_constraint('ck_shirts_condition_rating', 'condition_rating BETWEEN 1 AND 10')


def downgrade():
    with op.batch_alter_table('shirts') as batch_op:
        batch_op.drop_constraint('ck_shirts_condition_rating', type_='check')
        batch_op.drop_column('condition_notes')
        batch_op.drop_column('condition_rating')
