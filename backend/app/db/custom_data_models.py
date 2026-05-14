"""User-uploaded custom datasets + their rankings.

Sport-agnostic. A `CustomDataset` is a user "project" — one or more uploaded
`DatasetSegment`s (e.g. "2024 season", "2025 season") share a name column and
a union schema. Rows live in `DatasetRow` keyed by a normalized entity_key so
rankings can aggregate the same entity across segments. `CustomDatasetRanking`
holds the user's category config + computed results, mirroring SavedRanking's
share-mode lifecycle.
"""
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.database import Base


class CustomDataset(Base):
    __tablename__ = "custom_datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(Text, nullable=False)
    name_column = Column(Text, nullable=False)
    # Union schema across all segments: [{"name": str, "dtype": "numeric"|"text"}, ...]
    column_schema = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    segments = relationship(
        "DatasetSegment",
        back_populates="dataset",
        cascade="all, delete-orphan",
        order_by="DatasetSegment.created_at",
    )
    rankings = relationship(
        "CustomDatasetRanking",
        back_populates="dataset",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_custom_datasets_user_id", "user_id"),
    )


class DatasetSegment(Base):
    __tablename__ = "dataset_segments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        Integer,
        ForeignKey("custom_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    label = Column(Text, nullable=False)
    source_filename = Column(Text, nullable=True)
    row_count = Column(Integer, nullable=False, default=0)
    # Schema for THIS upload (subset of dataset.column_schema after reconciliation)
    segment_schema = Column(JSONB, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    dataset = relationship("CustomDataset", back_populates="segments")
    rows = relationship(
        "DatasetRow", back_populates="segment", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint("dataset_id", "label", name="uq_dataset_segments_label"),
        Index("ix_dataset_segments_dataset_id", "dataset_id"),
    )


class DatasetRow(Base):
    __tablename__ = "dataset_rows"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # dataset_id is denormalized from segment for fast cross-segment slicing.
    dataset_id = Column(
        Integer,
        ForeignKey("custom_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    segment_id = Column(
        Integer,
        ForeignKey("dataset_segments.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_key = Column(Text, nullable=False)  # normalized for cross-segment matching
    entity_name = Column(Text, nullable=False)  # raw name from the upload
    data = Column(JSONB, nullable=False)  # {column: value} excluding the name column

    segment = relationship("DatasetSegment", back_populates="rows")

    __table_args__ = (
        Index("ix_dataset_rows_dataset_entity", "dataset_id", "entity_key"),
        Index("ix_dataset_rows_segment_id", "segment_id"),
    )


class CustomDatasetRanking(Base):
    __tablename__ = "custom_dataset_rankings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(
        Integer,
        ForeignKey("custom_datasets.id", ondelete="CASCADE"),
        nullable=False,
    )
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title = Column(Text, nullable=False)
    # [{"id", "name", "weight", "stats": [{"name", "lower_is_better": bool}, ...]}, ...]
    categories = Column(JSONB, nullable=False)
    mode = Column(Text, nullable=False, server_default="single")
    segment_ids = Column(JSONB, nullable=False)  # [int, int, ...]
    games_column = Column(Text, nullable=True)
    min_rows = Column(Integer, nullable=False, server_default="1")

    share_mode = Column(Text, nullable=False, server_default="none")
    share_slug = Column(Text, nullable=True, unique=True)
    results_json = Column(JSONB, nullable=True)
    results_computed_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    dataset = relationship("CustomDataset", back_populates="rankings")

    __table_args__ = (
        CheckConstraint(
            "mode in ('single','cumulative','per_game')",
            name="ck_custom_dataset_rankings_mode",
        ),
        CheckConstraint(
            "share_mode in ('none','live','frozen')",
            name="ck_custom_dataset_rankings_share_mode",
        ),
        Index("ix_custom_dataset_rankings_user_id", "user_id"),
        Index("ix_custom_dataset_rankings_dataset_id", "dataset_id"),
    )
