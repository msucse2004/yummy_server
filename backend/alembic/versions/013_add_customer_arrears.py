"""Add arrears (미수금액) to customers

Revision ID: 013
Revises: 012
Create Date: 2025-02-17

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("arrears", sa.Numeric(14, 2), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "arrears")
