"""Add editable bilingual information pages, initially unpublished."""
from alembic import op
import sqlalchemy as sa

revision = 'e82c4319a670'
down_revision = 'd24a9b73c861'
branch_labels = None
depends_on = None


def upgrade():
    pages = op.create_table('store_pages',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('slug', sa.String(100), nullable=False, unique=True),
        sa.Column('title_en', sa.String(160), nullable=False),
        sa.Column('title_it', sa.String(160), nullable=False),
        sa.Column('body_en', sa.Text(), nullable=False),
        sa.Column('body_it', sa.Text(), nullable=False),
        sa.Column('published', sa.Boolean(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False))
    op.bulk_insert(pages, [dict(slug=slug, title_en=en, title_it=it, body_en='', body_it='', published=False, position=i)
        for i, (slug, en, it) in enumerate([
            ('about', 'About Kitaly', 'Chi siamo'),
            ('shipping', 'Shipping & returns', 'Spedizioni e resi'),
            ('authenticity', 'Authenticity', 'Autenticità')])])


def downgrade():
    op.drop_table('store_pages')
