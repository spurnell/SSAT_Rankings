"""CSV/XLSX upload parser for the user-data Custom Rankings flow.

`parse_upload` validates the file, infers per-column dtypes, normalizes entity
keys, and returns rows ready to be inserted into `dataset_rows`.
`reconcile_schemas` compares a new upload's schema against an existing
dataset's column_schema and returns the drift (added / missing / type-mismatch
columns) so the caller can decide whether to accept the append.
"""
from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import pandas as pd

# Reuse the existing name normalizer so user-data entity keys follow the same
# rule as the NFL custom-categories join key.
from app.services.custom_categories import _normalize_name


MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB raw
MAX_ROWS = 10_000
MIN_ROWS = 10
MIN_COLUMNS = 2
NUMERIC_THRESHOLD = 0.9  # ≥ 90% of non-null values must parse as numeric


@dataclass
class ColumnSpec:
    name: str
    dtype: str  # "numeric" | "text"

    def as_dict(self) -> Dict[str, str]:
        return {"name": self.name, "dtype": self.dtype}


@dataclass
class ParsedRow:
    entity_key: str
    entity_name: str
    data: Dict[str, Any]


@dataclass
class ParsedUpload:
    schema: List[ColumnSpec]
    rows: List[ParsedRow]
    name_column: str
    duplicate_entity_keys: List[str] = field(default_factory=list)


@dataclass
class SchemaDrift:
    added: List[ColumnSpec]
    missing: List[str]
    type_mismatches: List[Dict[str, str]]  # [{name, dataset_dtype, segment_dtype}]

    @property
    def has_breaking_changes(self) -> bool:
        return bool(self.type_mismatches)

    @property
    def is_empty(self) -> bool:
        return not (self.added or self.missing or self.type_mismatches)


class ParseError(ValueError):
    """Validation error surfaced to the API as HTTP 400."""


def _read_dataframe(filename: str, raw: bytes) -> pd.DataFrame:
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    if ext == "csv":
        return pd.read_csv(io.BytesIO(raw))
    if ext in ("xlsx", "xlsm"):
        return pd.read_excel(io.BytesIO(raw), engine="openpyxl")
    raise ParseError(f"Unsupported file type '.{ext}'. Use .csv or .xlsx.")


def _infer_dtype(series: pd.Series) -> str:
    non_null = series.dropna()
    if non_null.empty:
        return "text"
    coerced = pd.to_numeric(non_null, errors="coerce")
    if coerced.notna().mean() >= NUMERIC_THRESHOLD:
        return "numeric"
    return "text"


def _coerce_value(value: Any, dtype: str) -> Any:
    if pd.isna(value):
        return None
    if dtype == "numeric":
        num = pd.to_numeric(value, errors="coerce")
        if pd.isna(num):
            return None
        return float(num)
    return str(value)


def parse_upload(
    filename: str, raw: bytes, name_column: Optional[str]
) -> ParsedUpload:
    """Parse a user upload into rows + schema. Raises ParseError on invalid input.

    `name_column` is mandatory; the caller knows it from the form submission
    (or, for the very first upload, picks it from the schema preview).
    """
    if not raw:
        raise ParseError("Empty file.")
    if len(raw) > MAX_FILE_BYTES:
        raise ParseError(
            f"File too large ({len(raw)} bytes). Limit is {MAX_FILE_BYTES} bytes."
        )
    if not name_column:
        raise ParseError("name_column is required.")

    df = _read_dataframe(filename, raw)
    df = df.dropna(how="all")  # drop fully-empty rows

    if df.shape[1] < MIN_COLUMNS:
        raise ParseError(f"Need at least {MIN_COLUMNS} columns; got {df.shape[1]}.")
    if df.shape[0] < MIN_ROWS:
        raise ParseError(f"Need at least {MIN_ROWS} rows; got {df.shape[0]}.")
    if df.shape[0] > MAX_ROWS:
        raise ParseError(f"Too many rows ({df.shape[0]}). Limit is {MAX_ROWS}.")
    if name_column not in df.columns:
        raise ParseError(
            f"name_column '{name_column}' not found. "
            f"Available columns: {list(df.columns)}"
        )

    # Build schema for every column EXCEPT the name column. The name column is
    # always treated as the entity identifier.
    schema: List[ColumnSpec] = []
    for col in df.columns:
        if col == name_column:
            continue
        schema.append(ColumnSpec(name=str(col), dtype=_infer_dtype(df[col])))

    numeric_count = sum(1 for c in schema if c.dtype == "numeric")
    if numeric_count < 1:
        raise ParseError("At least one numeric column (besides the name column) is required.")

    # Build rows, deduping by normalized entity_key (first occurrence wins).
    rows: List[ParsedRow] = []
    duplicates: List[str] = []
    seen: Dict[str, int] = {}
    for _, raw_row in df.iterrows():
        raw_name = raw_row.get(name_column)
        if pd.isna(raw_name) or str(raw_name).strip() == "":
            continue
        entity_name = str(raw_name).strip()
        entity_key = _normalize_name(entity_name)
        if not entity_key:
            continue
        if entity_key in seen:
            duplicates.append(entity_name)
            continue
        seen[entity_key] = 1

        data: Dict[str, Any] = {}
        for col_spec in schema:
            data[col_spec.name] = _coerce_value(raw_row.get(col_spec.name), col_spec.dtype)
        rows.append(
            ParsedRow(entity_key=entity_key, entity_name=entity_name, data=data)
        )

    if not rows:
        raise ParseError("No valid entity rows after parsing.")

    return ParsedUpload(
        schema=schema,
        rows=rows,
        name_column=name_column,
        duplicate_entity_keys=duplicates,
    )


def reconcile_schemas(
    dataset_schema: List[Dict[str, str]],
    segment_schema: List[ColumnSpec],
) -> SchemaDrift:
    """Compare a new upload's schema against the dataset's union schema."""
    dataset_by_name = {c["name"]: c["dtype"] for c in dataset_schema}
    segment_by_name = {c.name: c.dtype for c in segment_schema}

    added: List[ColumnSpec] = [
        c for c in segment_schema if c.name not in dataset_by_name
    ]
    missing: List[str] = [n for n in dataset_by_name if n not in segment_by_name]
    type_mismatches: List[Dict[str, str]] = []
    for name, dtype in segment_by_name.items():
        if name in dataset_by_name and dataset_by_name[name] != dtype:
            type_mismatches.append(
                {
                    "name": name,
                    "dataset_dtype": dataset_by_name[name],
                    "segment_dtype": dtype,
                }
            )

    return SchemaDrift(added=added, missing=missing, type_mismatches=type_mismatches)


def merge_schemas(
    dataset_schema: List[Dict[str, str]],
    drift: SchemaDrift,
) -> List[Dict[str, str]]:
    """Apply a drift's `added` columns to the dataset schema."""
    out = list(dataset_schema)
    for col in drift.added:
        out.append(col.as_dict())
    return out
