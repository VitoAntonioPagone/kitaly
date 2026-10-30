"""Add optional garment measurements."""
from alembic import op
import sqlalchemy as sa
revision = 'f48c3e82b761'
down_revision = 'e82c4319a670'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('shirts', sa.Column('dimensions', sa.Text(), nullable=True))

def downgrade():
    op.drop_column('shirts', 'dimensions')
