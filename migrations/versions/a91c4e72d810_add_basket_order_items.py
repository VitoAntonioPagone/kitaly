"""Add item snapshots and unique reservations for multi-shirt checkout."""
from alembic import op
import sqlalchemy as sa

revision = 'a91c4e72d810'
down_revision = 'f13a9c72e645'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('payment_order_items',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('order_id', sa.String(32), sa.ForeignKey('payment_orders.id'), nullable=False),
        sa.Column('shirt_id', sa.Integer(), sa.ForeignKey('shirts.id'), nullable=False),
        sa.Column('active_shirt_id', sa.Integer(), nullable=True, unique=True),
        sa.Column('product_name', sa.String(500), nullable=False),
        sa.Column('product_code', sa.Integer(), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.UniqueConstraint('order_id', 'shirt_id', name='uq_order_item_shirt'))
    op.create_index('ix_payment_order_items_order_id', 'payment_order_items', ['order_id'])
    op.execute(sa.text('INSERT INTO payment_order_items '
        '(order_id, shirt_id, active_shirt_id, product_name, product_code, amount) '
        'SELECT id, shirt_id, active_shirt_id, product_name, product_code, amount_subtotal FROM payment_orders'))


def downgrade():
    op.drop_table('payment_order_items')
