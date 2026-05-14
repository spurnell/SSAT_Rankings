"use client";

import { DatasetRankingMode, DatasetSegmentSummary, ColumnSchemaEntry } from "@/lib/authApi";

interface SegmentMultiSelectProps {
  segments: DatasetSegmentSummary[];
  selectedIds: number[];
  mode: DatasetRankingMode;
  gamesColumn: string | null;
  numericColumns: ColumnSchemaEntry[];
  onChange: (next: {
    selectedIds: number[];
    mode: DatasetRankingMode;
    gamesColumn: string | null;
  }) => void;
}

const MODE_LABELS: Record<DatasetRankingMode, string> = {
  single: "Single segment",
  cumulative: "Cumulative (sum across segments)",
  per_game: "Per-game (divide by games column)",
};

export default function SegmentMultiSelect({
  segments,
  selectedIds,
  mode,
  gamesColumn,
  numericColumns,
  onChange,
}: SegmentMultiSelectProps) {
  function toggleSegment(id: number) {
    let next: number[];
    if (selectedIds.includes(id)) next = selectedIds.filter((x) => x !== id);
    else next = [...selectedIds, id];
    let nextMode = mode;
    if (next.length <= 1 && mode !== "single") nextMode = "single";
    onChange({ selectedIds: next, mode: nextMode, gamesColumn });
  }

  function setMode(m: DatasetRankingMode) {
    onChange({ selectedIds, mode: m, gamesColumn });
  }

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Segments to include
        </label>
        <ul className="space-y-1">
          {segments.map((s) => (
            <li key={s.id}>
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input
                  type="checkbox"
                  checked={selectedIds.includes(s.id)}
                  onChange={() => toggleSegment(s.id)}
                />
                <span className="font-medium text-slate-900">{s.label}</span>
                <span className="text-xs text-slate-500">({s.row_count} rows)</span>
              </label>
            </li>
          ))}
        </ul>
      </div>

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-2">
          Aggregation mode
        </label>
        <div className="space-y-1">
          {(["single", "cumulative", "per_game"] as DatasetRankingMode[]).map((m) => {
            const disabled = m !== "single" && selectedIds.length < 2;
            return (
              <label
                key={m}
                className={`flex items-center gap-2 text-sm ${disabled ? "text-slate-400" : "text-slate-700"}`}
              >
                <input
                  type="radio"
                  name="mode"
                  checked={mode === m}
                  disabled={disabled}
                  onChange={() => setMode(m)}
                />
                {MODE_LABELS[m]}
              </label>
            );
          })}
        </div>
        <p className="text-xs text-slate-500 mt-1">
          Single mode ranks rows within one segment. Cumulative and per-game
          group rows by name across the selected segments.
        </p>
      </div>

      {mode === "per_game" && (
        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Games column
          </label>
          <select
            value={gamesColumn ?? ""}
            onChange={(e) =>
              onChange({ selectedIds, mode, gamesColumn: e.target.value || null })
            }
            className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm"
          >
            <option value="">— select numeric column —</option>
            {numericColumns.map((c) => (
              <option key={c.name} value={c.name}>
                {c.name}
              </option>
            ))}
          </select>
          <p className="text-xs text-slate-500 mt-1">
            Summed stats are divided by the sum of this column per entity.
          </p>
        </div>
      )}
    </div>
  );
}
