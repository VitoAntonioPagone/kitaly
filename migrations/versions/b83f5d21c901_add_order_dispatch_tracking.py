"""Add saved tracking details and durable email delivery state."""
from alembic import op
import sqlalchemy as sa

revision = 'b83f5d21c901'
down_revision = 'a91c4e72d810'
branch_labels = None
depends_on = None


def upgrade():
    for column in [
        sa.Column('shipping_carrier', sa.String(100)),
        sa.Column('tracking_url', sa.String(2048)),
        sa.Column('dispatched_at', sa.DateTime()),
        sa.Column('tracking_email_state', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('tracking_email_sent_at', sa.DateTime()),
        sa.Column('tracking_email_started_at', sa.DateTime()),
        sa.Column('tracking_email_fingerprint', sa.String(64)),
        sa.Column('tracking_email_error', sa.String(255)),
    ]:
        op.add_column('payment_orders', column)


def downgrade():
    for name in ['tracking_email_error', 'tracking_email_fingerprint', 'tracking_email_started_at', 'tracking_email_sent_at',
                 'tracking_email_state', 'dispatched_at', 'tracking_url', 'shipping_carrier']:
        op.drop_column('payment_orders', name)
