"""Add app_settings table

Revision ID: 006
Revises: 005
Create Date: 2025-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(64), primary_key=True),
        sa.Column("value", sa.String(256), nullable=False),
    )
    op.execute(
        sa.text("INSERT INTO app_settings (key, value) VALUES ('delivery_route_count', '5')")
    )


def downgrade() -> None:
    op.drop_table("app_settings")
