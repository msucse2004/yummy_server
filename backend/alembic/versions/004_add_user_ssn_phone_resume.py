"""Add ssn, phone, resume to users

Revision ID: 004
Revises: 003
Create Date: 2025-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("ssn", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column("users", sa.Column("resume", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "resume")
    op.drop_column("users", "phone")
    op.drop_column("users", "ssn")
