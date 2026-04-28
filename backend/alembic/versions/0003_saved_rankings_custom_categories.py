"""saved_rankings: add categories column, allow null weights

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-28
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # User-defined categories (custom-category builder). Null when the ranking
    # uses the default categories with weight tuning.
    op.add_column(
        "saved_rankings",
        sa.Column("categories", JSONB(), nullable=True),
    )
    # Weights becomes nullable: custom-category rankings store their weights
    # inside the categories JSON, not in the weights column.
    op.alter_column(
        "saved_rankings",
        "weights",
        existing_type=JSONB(),
        nullable=True,
    )


def downgrade() -> None:
    op.alter_column(
        "saved_rankings",
        "weights",
        existing_type=JSONB(),
        nullable=False,
    )
    op.drop_column("saved_rankings", "categories")
