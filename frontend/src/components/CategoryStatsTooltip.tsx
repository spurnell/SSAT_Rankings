"use client";

import { CategoryInfo } from "@/lib/api";
import { getStatLabel } from "@/lib/statLabels";

interface CategoryStatsTooltipProps {
  category: CategoryInfo;
  className?: string;
}

/**
 * Small dark tooltip that lists the underlying stats for a ranking category.
 * Positioned by its parent (use with `relative` parent + absolute positioning classes).
 */
export default function CategoryStatsTooltip({
  category,
  className = "",
}: CategoryStatsTooltipProps) {
  const stats = category.stats || [];

  return (
    <div
      role="tooltip"
      className={`pointer-events-none z-50 w-56 rounded-md border border-slate-700 bg-slate-800 px-3 py-2 text-left shadow-xl ${className}`}
    >
      <div className="mb-1 border-b border-slate-700 pb-1 text-xs font-semibold uppercase tracking-wider text-blue-300">
        {category.name}
      </div>
      {stats.length > 0 ? (
        <ul className="space-y-0.5 text-xs text-slate-100">
          {stats.map((stat) => (
            <li key={stat} className="leading-snug">
              <span className="mr-1 text-slate-500">•</span>
              {getStatLabel(stat)}
            </li>
          ))}
        </ul>
      ) : (
        <div className="text-xs italic text-slate-400">No stat breakdown available</div>
      )}
    </div>
  );
}
