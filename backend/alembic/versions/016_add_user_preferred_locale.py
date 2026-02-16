"""Add preferred_locale to users

Revision ID: 016
Revises: 015
Create Date: 2025-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "preferred_locale",
            sa.String(64),
            nullable=True,
            server_default=sa.text("'대한민국'"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "preferred_locale")
