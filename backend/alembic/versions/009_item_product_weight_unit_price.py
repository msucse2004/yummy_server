"""Item: name->product, add weight, price->unit_price, code required

Revision ID: 009
Revises: 008
Create Date: 2025-02-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    # Add new columns (nullable first)
    op.add_column("items", sa.Column("product", sa.String(128), nullable=True))
    op.add_column("items", sa.Column("weight", sa.Numeric(14, 2), nullable=True))
    op.add_column("items", sa.Column("unit_price", sa.Numeric(14, 2), nullable=True))
    # Migrate data
    conn.execute(sa.text("UPDATE items SET product = name, unit_price = price"))
    # Fill code for rows where null: P00001, P00002, ...
    conn.execute(
        sa.text(
            "UPDATE items SET code = 'P' || LPAD(id::text, 5, '0') WHERE code IS NULL OR code = ''"
        )
    )
    # Make code not null, product not null
    op.alter_column(
        "items", "code", existing_type=sa.String(64), nullable=False
    )
    op.alter_column(
        "items", "product", existing_type=sa.String(128), nullable=False
    )
    # Drop old columns
    op.drop_index("ix_items_name", "items", if_exists=True)
    op.drop_column("items", "name")
    op.drop_column("items", "price")
    op.create_index("ix_items_product", "items", ["product"], unique=False)


def downgrade() -> None:
    op.add_column("items", sa.Column("name", sa.String(128), nullable=True))
    op.add_column("items", sa.Column("price", sa.Numeric(14, 2), nullable=True))
    conn = op.get_bind()
    conn.execute(sa.text("UPDATE items SET name = product, price = unit_price"))
    op.alter_column("items", "name", nullable=False)
    op.drop_index("ix_items_product", "items", if_exists=True)
    op.drop_column("items", "product")
    op.drop_column("items", "weight")
    op.drop_column("items", "unit_price")
    op.alter_column("items", "code", nullable=True)
    op.create_index("ix_items_name", "items", ["name"], unique=False)
