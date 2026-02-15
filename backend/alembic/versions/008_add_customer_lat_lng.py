"""Add latitude/longitude to customers

Revision ID: 008
Revises: 007
Create Date: 2025-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("latitude", sa.Numeric(10, 7), nullable=True))
    op.add_column("customers", sa.Column("longitude", sa.Numeric(11, 7), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "longitude")
    op.drop_column("customers", "latitude")
