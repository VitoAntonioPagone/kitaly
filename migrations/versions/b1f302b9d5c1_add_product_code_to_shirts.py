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

    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.add_column(sa.Column('product_code', sa.Integer(), nullable=True))

    # Backfill existing rows in creation order (oldest first, stable by id).
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
                    ORDER BY
                      CASE WHEN created_at IS NULL THEN 1 ELSE 0 END,
                      created_at ASC,
                      id ASC
                  ) AS ordered
                  JOIN (SELECT @rownum := 0) AS vars
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
                    ROW_NUMBER() OVER (
                      ORDER BY
                        CASE WHEN created_at IS NULL THEN 1 ELSE 0 END,
                        created_at ASC,
                        id ASC
                    ) AS new_code
                  FROM shirts
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

    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.alter_column('product_code', existing_type=sa.Integer(), nullable=False)
        batch_op.create_unique_constraint('uq_shirts_product_code', ['product_code'])

    # DB-level auto-increment behavior for future inserts + manual override protection.
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
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME}"))
        op.execute(
            sa.text(
                f"""
                CREATE TRIGGER {TRIGGER_NAME}
                BEFORE INSERT ON shirts
                FOR EACH ROW
                BEGIN
                    UPDATE {SEQ_TABLE}
                    SET next_val = LAST_INSERT_ID(next_val + 1)
                    WHERE id = 1;
                    SET NEW.product_code = LAST_INSERT_ID() - 1;
                END
                """
            )
        )


def downgrade():
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == 'mysql':
        op.execute(sa.text(f"DROP TRIGGER IF EXISTS {TRIGGER_NAME}"))
        op.execute(sa.text(f"DROP TABLE IF EXISTS {SEQ_TABLE}"))

    with op.batch_alter_table('shirts', schema=None) as batch_op:
        batch_op.drop_constraint('uq_shirts_product_code', type_='unique')
        batch_op.drop_column('product_code')
