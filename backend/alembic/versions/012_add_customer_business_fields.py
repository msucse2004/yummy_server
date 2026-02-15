"""Add business fields to customers: business_registration_number, representative_name, business_type, business_category

Revision ID: 012
Revises: 011
Create Date: 2025-02-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: str | None = "011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("business_registration_number", sa.String(32), nullable=True))
    op.add_column("customers", sa.Column("representative_name", sa.String(64), nullable=True))
    op.add_column("customers", sa.Column("business_type", sa.String(64), nullable=True))
    op.add_column("customers", sa.Column("business_category", sa.String(64), nullable=True))


def downgrade() -> None:
    op.drop_column("customers", "business_category")
    op.drop_column("customers", "business_type")
    op.drop_column("customers", "representative_name")
    op.drop_column("customers", "business_registration_number")
