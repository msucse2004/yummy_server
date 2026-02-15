"""Add description to items

Revision ID: 010
Revises: 009
Create Date: 2025-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("items", sa.Column("description", sa.String(256), nullable=True))


def downgrade() -> None:
    op.drop_column("items", "description")
