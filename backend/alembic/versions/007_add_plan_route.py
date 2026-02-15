"""Add route column to plans

Revision ID: 007
Revises: 006
Create Date: 2025-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("plans", sa.Column("route", sa.String(32), nullable=True))


def downgrade() -> None:
    op.drop_column("plans", "route")
