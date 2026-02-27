"""add product_code to shirts

Revision ID: b1f302b9d5c1
Revises: 9a2b6c1d0f4a
Create Date: 2026-02-27 14:20:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b1f302b9d5c1'
down_revision = '9a2b6c1d0f4a'
branch_labels = None
depends_on = None


TRIGGER_NAME = 'shirts_before_insert_product_code'
SEQ_TABLE = 'shirt_product_code_seq'


def upgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name
    inspector = sa.inspect(bind)
    columns = {col['name']: col for col in inspector.get_columns('shirts')}

    if 'product_code' not in columns:
        with op.batch_alter_table('shirts', schema=None) as batch_op:
            batch_op.add_column(sa.Column('product_code', sa.Integer(), nullable=True))

    # Backfill only missing rows, preserving already assigned codes in partial/failed runs.
    if dialect == 'mysql':
        op.execute(
            sa.text(
                """
                UPDATE shirts AS s
                JOIN (
                  SELECT ordered.id, (@rownum := @rownum + 1) AS new_code
                  FROM (
                    SELECT id
                    FROM shirts
                    WHERE product_code IS NULL
                    ORDER BY
                      CASE WHEN created_at IS NULL THEN 1 ELSE 0 END,
                      created_at ASC,
                      id ASC
                  ) AS ordered
                  JOIN (SELECT @rownum := (SELECT COALESCE(MAX(product_code), 0) FROM shirts)) AS vars
                ) AS ranked ON ranked.id = s.id
                SET s.product_code = ranked.new_code
                """
            )
        )
    else:
        op.execute(
            sa.text(
                """
                WITH ranked AS (
                  SELECT
                    id,
                    (
                      SELECT COALESCE(MAX(product_code), 0) FROM shirts
                    ) + ROW_NUMBER() OVER (
                      ORDER BY
                        CASE WHEN created_at IS NULL THEN 1 ELSE 0 END,
                        created_at ASC,
                        id ASC
                    ) AS new_code
                  FROM shirts
                  WHERE product_code IS NULL
                )
                UPDATE shirts
                SET product_code = (
                  SELECT ranked.new_code
                  FROM ranked
                  WHERE ranked.id = shirts.id
                )
                """
            )
        )

    # Enforce non-null + unique.
    null_count = bind.execute(sa.text("SELECT COUNT(*) FROM shirts WHERE product_code IS NULL")).scalar() or 0
    if null_count:
        raise RuntimeError("Cannot enforce product_code constraints: NULL values still present.")

    columns = {col['name']: col for col in sa.inspect(bind).get_columns('shirts')}
    if columns.get('product_code', {}).get('nullable', True):
        with op.batch_alter_table('shirts', schema=None) as batch_op:
            batch_op.alter_column('product_code', existing_type=sa.Integer(), nullable=False)

    unique_constraints = sa.inspect(bind).get_unique_constraints('shirts')
    has_product_code_unique = any(
        set(constraint.get('column_names') or []) == {'product_code'}
        for constraint in unique_constraints
    )
    if not has_product_code_unique:
        with op.batch_alter_table('shirts', schema=None) as batch_op:
            batch_op.create_unique_constraint('uq_shirts_product_code', ['product_code'])

    # Sequence table for backend-side atomic allocator (no trigger required).
    if dialect == 'mysql':
        op.execute(
            sa.text(
                f"""
                CREATE TABLE IF NOT EXISTS {SEQ_TABLE} (
                    id TINYINT NOT NULL PRIMARY KEY,
                    next_val INT NOT NULL
                )
                """
            )
        )
        op.execute(
            sa.text(
                f"""
                INSERT INTO {SEQ_TABLE} (id, next_val)
                VALUES (1, (SELECT COALESCE(MAX(product_code), 0) + 1 FROM shirts))
                ON DUPLICATE KEY UPDATE
                    next_val = GREATEST(next_val, VALUES(next_val))
                """
            )
        )
        # Cleanup from earlier migration attempt.
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME}"))


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'mysql':
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME}"))
        op.execute(sa.text(f"DROP TABLE IF EXISTS {SEQ_TABLE}"))

    inspector = sa.inspect(bind)
    unique_constraints = inspector.get_unique_constraints('shirts')
    has_product_code_unique = any(
        set(constraint.get('column_names') or []) == {'product_code'}
        for constraint in unique_constraints
    )
    columns = {col['name'] for col in inspector.get_columns('shirts')}

    with op.batch_alter_table('shirts', schema=None) as batch_op:
        if has_product_code_unique:
            batch_op.drop_constraint('uq_shirts_product_code', type_='unique')
        if 'product_code' in columns:
            batch_op.drop_column('product_code')
