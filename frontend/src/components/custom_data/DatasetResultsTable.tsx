"use client";

import { DatasetRankingCategory, DatasetRankingResultRow } from "@/lib/authApi";

interface DatasetResultsTableProps {
  results: DatasetRankingResultRow[];
  categories: DatasetRankingCategory[];
  showSegments: boolean;
}

export default function DatasetResultsTable({
  results,
  categories,
  showSegments,
}: DatasetResultsTableProps) {
  if (results.length === 0) {
    return (
      <p className="text-sm text-slate-500">
        No results — the configuration produced an empty ranking. Check your
        segment selection and that at least one numeric column is included.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm">
        <thead className="bg-slate-100 text-slate-700">
          <tr>
            <th className="text-left px-3 py-2 font-medium">#</th>
            <th className="text-left px-3 py-2 font-medium">Entity</th>
            <th className="text-right px-3 py-2 font-medium">Overall</th>
            {categories.map((c) => (
              <th key={c.id} className="text-right px-3 py-2 font-medium">
                {c.name}
              </th>
            ))}
            {showSegments && (
              <th className="text-left px-3 py-2 font-medium">Segments</th>
            )}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {results.map((r, i) => (
            <tr key={`${r.entity_key}-${i}`} className="hover:bg-slate-50">
              <td className="px-3 py-2 text-slate-500">{i + 1}</td>
              <td className="px-3 py-2 font-medium text-slate-900">
                {r.entity_name}
              </td>
              <td className="px-3 py-2 text-right font-semibold text-slate-900">
                {r.overall_score.toFixed(1)}
              </td>
              {categories.map((c) => (
                <td key={c.id} className="px-3 py-2 text-right text-slate-700">
                  {r.category_scores[c.id] != null
                    ? r.category_scores[c.id].toFixed(1)
                    : "—"}
                </td>
              ))}
              {showSegments && (
                <td className="px-3 py-2 text-xs text-slate-600">
                  {r.contributing_segments.map((s) => (
                    <span
                      key={s}
                      className="inline-block mr-1 px-1.5 py-0.5 rounded bg-slate-100 border border-slate-200"
                    >
                      {s}
                    </span>
                  ))}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
