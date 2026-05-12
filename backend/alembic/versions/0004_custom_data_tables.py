"""custom user-uploaded datasets and rankings

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-12
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "custom_datasets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("name_column", sa.Text(), nullable=False),
        sa.Column("column_schema", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_custom_datasets_user_id", "custom_datasets", ["user_id"])

    op.create_table(
        "dataset_segments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("custom_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("source_filename", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("segment_schema", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("dataset_id", "label", name="uq_dataset_segments_label"),
    )
    op.create_index(
        "ix_dataset_segments_dataset_id", "dataset_segments", ["dataset_id"]
    )

    op.create_table(
        "dataset_rows",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("custom_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "segment_id",
            sa.Integer(),
            sa.ForeignKey("dataset_segments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("entity_key", sa.Text(), nullable=False),
        sa.Column("entity_name", sa.Text(), nullable=False),
        sa.Column("data", JSONB(), nullable=False),
    )
    op.create_index(
        "ix_dataset_rows_dataset_entity",
        "dataset_rows",
        ["dataset_id", "entity_key"],
    )
    op.create_index("ix_dataset_rows_segment_id", "dataset_rows", ["segment_id"])

    op.create_table(
        "custom_dataset_rankings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "dataset_id",
            sa.Integer(),
            sa.ForeignKey("custom_datasets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("categories", JSONB(), nullable=False),
        sa.Column("mode", sa.Text(), nullable=False, server_default="single"),
        sa.Column("segment_ids", JSONB(), nullable=False),
        sa.Column("games_column", sa.Text(), nullable=True),
        sa.Column("min_rows", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("share_mode", sa.Text(), nullable=False, server_default="none"),
        sa.Column("share_slug", sa.Text(), nullable=True),
        sa.Column("results_json", JSONB(), nullable=True),
        sa.Column("results_computed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint("share_slug", name="uq_custom_dataset_rankings_share_slug"),
        sa.CheckConstraint(
            "mode in ('single','cumulative','per_game')",
            name="ck_custom_dataset_rankings_mode",
        ),
        sa.CheckConstraint(
            "share_mode in ('none','live','frozen')",
            name="ck_custom_dataset_rankings_share_mode",
        ),
    )
    op.create_index(
        "ix_custom_dataset_rankings_user_id",
        "custom_dataset_rankings",
        ["user_id"],
    )
    op.create_index(
        "ix_custom_dataset_rankings_dataset_id",
        "custom_dataset_rankings",
        ["dataset_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_custom_dataset_rankings_dataset_id", table_name="custom_dataset_rankings"
    )
    op.drop_index(
        "ix_custom_dataset_rankings_user_id", table_name="custom_dataset_rankings"
    )
    op.drop_table("custom_dataset_rankings")

    op.drop_index("ix_dataset_rows_segment_id", table_name="dataset_rows")
    op.drop_index("ix_dataset_rows_dataset_entity", table_name="dataset_rows")
    op.drop_table("dataset_rows")

    op.drop_index("ix_dataset_segments_dataset_id", table_name="dataset_segments")
    op.drop_table("dataset_segments")

    op.drop_index("ix_custom_datasets_user_id", table_name="custom_datasets")
    op.drop_table("custom_datasets")
