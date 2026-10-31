"""Add durable Stripe orders and unique inventory reservations."""
from alembic import op
import sqlalchemy as sa

revision = 'f13a9c72e645'
down_revision = 'f48c3e82b761'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'payment_orders',
        sa.Column('id', sa.String(32), primary_key=True),
        sa.Column('shirt_id', sa.Integer(), sa.ForeignKey('shirts.id'), nullable=False),
        sa.Column('active_shirt_id', sa.Integer(), unique=True, nullable=True),
        sa.Column('product_name', sa.String(500), nullable=False),
        sa.Column('product_code', sa.Integer(), nullable=False),
        sa.Column('amount_subtotal', sa.Integer(), nullable=False),
        sa.Column('shipping_amount', sa.Integer(), nullable=False),
        sa.Column('currency', sa.String(3), nullable=False),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('checkout_session_id', sa.String(255), unique=True, nullable=True),
        sa.Column('checkout_params', sa.JSON(), nullable=False),
        sa.Column('payment_intent_id', sa.String(255), nullable=True),
        sa.Column('customer_email', sa.String(800), nullable=True),
        sa.Column('customer_name', sa.String(255), nullable=True),
        sa.Column('shipping_details', sa.JSON(), nullable=True),
        sa.Column('amount_total', sa.Integer(), nullable=True),
        sa.Column('livemode', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_payment_orders_shirt_id', 'payment_orders', ['shirt_id'])


def downgrade():
    op.drop_index('ix_payment_orders_shirt_id', table_name='payment_orders')
    op.drop_table('payment_orders')
