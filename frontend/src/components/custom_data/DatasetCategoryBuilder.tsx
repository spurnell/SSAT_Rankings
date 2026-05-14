"use client";

import { ColumnSchemaEntry, DatasetRankingCategory, DatasetRankingStat } from "@/lib/authApi";

interface DatasetCategoryBuilderProps {
  categories: DatasetRankingCategory[];
  numericColumns: ColumnSchemaEntry[];
  onChange: (next: DatasetRankingCategory[]) => void;
}

function emptyCategory(idx: number): DatasetRankingCategory {
  return {
    id: `cat_${Date.now()}_${idx}`,
    name: `Category ${idx + 1}`,
    weight: 1,
    stats: [],
  };
}

export default function DatasetCategoryBuilder({
  categories,
  numericColumns,
  onChange,
}: DatasetCategoryBuilderProps) {
  function updateCategory(idx: number, patch: Partial<DatasetRankingCategory>) {
    onChange(categories.map((c, i) => (i === idx ? { ...c, ...patch } : c)));
  }

  function removeCategory(idx: number) {
    onChange(categories.filter((_, i) => i !== idx));
  }

  function addCategory() {
    onChange([...categories, emptyCategory(categories.length)]);
  }

  function toggleStat(idx: number, name: string) {
    const cat = categories[idx];
    const existing = cat.stats.find((s) => s.name === name);
    let nextStats: DatasetRankingStat[];
    if (existing) nextStats = cat.stats.filter((s) => s.name !== name);
    else nextStats = [...cat.stats, { name, lower_is_better: false }];
    updateCategory(idx, { stats: nextStats });
  }

  function setLowerIsBetter(idx: number, name: string, value: boolean) {
    const cat = categories[idx];
    const nextStats = cat.stats.map((s) =>
      s.name === name ? { ...s, lower_is_better: value } : s
    );
    updateCategory(idx, { stats: nextStats });
  }

  return (
    <div className="space-y-4">
      {categories.map((cat, idx) => (
        <div key={cat.id} className="rounded-lg border border-slate-200 p-4">
          <div className="flex flex-wrap items-center gap-3 mb-3">
            <input
              type="text"
              value={cat.name}
              onChange={(e) => updateCategory(idx, { name: e.target.value })}
              className="flex-1 min-w-[150px] rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-1.5 text-sm font-medium"
            />
            <label className="text-xs text-slate-600 flex items-center gap-1">
              Weight
              <input
                type="number"
                step="0.1"
                min="0"
                value={cat.weight}
                onChange={(e) =>
                  updateCategory(idx, { weight: Number(e.target.value) })
                }
                className="w-20 rounded-md border border-slate-300 bg-white text-slate-900 px-2 py-1 text-sm"
              />
            </label>
            <button
              onClick={() => removeCategory(idx)}
              className="ml-auto px-3 py-1 rounded-md border border-red-300 text-red-700 text-xs hover:bg-red-50"
            >
              Remove
            </button>
          </div>

          <div className="text-xs text-slate-600 mb-2">
            Pick numeric columns for this category. Check &quot;lower is better&quot; for
            stats where smaller values are better (e.g. errors, turnovers).
          </div>

          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1">
            {numericColumns.map((col) => {
              const selected = cat.stats.find((s) => s.name === col.name);
              return (
                <li
                  key={col.name}
                  className={`flex items-center gap-2 text-xs px-2 py-1 rounded ${
                    selected ? "bg-blue-50" : "hover:bg-slate-50"
                  }`}
                >
                  <label className="flex items-center gap-2 flex-1 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={!!selected}
                      onChange={() => toggleStat(idx, col.name)}
                    />
                    <code className="text-slate-900">{col.name}</code>
                  </label>
                  {selected && (
                    <label className="text-xs text-slate-600 flex items-center gap-1">
                      <input
                        type="checkbox"
                        checked={selected.lower_is_better}
                        onChange={(e) =>
                          setLowerIsBetter(idx, col.name, e.target.checked)
                        }
                      />
                      lower=better
                    </label>
                  )}
                </li>
              );
            })}
          </ul>
        </div>
      ))}

      <button
        onClick={addCategory}
        className="w-full px-4 py-2 rounded-md border border-dashed border-slate-300 text-sm text-slate-700 hover:bg-slate-50"
      >
        + Add category
      </button>
    </div>
  );
}
