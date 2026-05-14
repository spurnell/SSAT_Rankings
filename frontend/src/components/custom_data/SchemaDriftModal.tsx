"use client";

import { SchemaDrift } from "@/lib/authApi";

interface SchemaDriftModalProps {
  drift: SchemaDrift;
  onClose: () => void;
}

export default function SchemaDriftModal({ drift, onClose }: SchemaDriftModalProps) {
  const hasAny =
    drift.added.length > 0 ||
    drift.missing.length > 0 ||
    drift.type_mismatches.length > 0;

  if (!hasAny) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="bg-white rounded-xl shadow-xl max-w-lg w-full p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-slate-900 mb-2">
          Schema changes accepted
        </h3>
        <p className="text-sm text-slate-600 mb-4">
          The new segment didn&apos;t match the existing dataset schema exactly.
          Here&apos;s what changed:
        </p>

        {drift.added.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-semibold text-slate-700 uppercase tracking-wide mb-1">
              New columns added to the dataset
            </div>
            <ul className="text-sm text-slate-700 space-y-0.5">
              {drift.added.map((c) => (
                <li key={c.name}>
                  <code>{c.name}</code> ({c.dtype})
                </li>
              ))}
            </ul>
          </div>
        )}

        {drift.missing.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">
              Columns missing in this segment
            </div>
            <ul className="text-sm text-slate-700 space-y-0.5">
              {drift.missing.map((name) => (
                <li key={name}>
                  <code>{name}</code> — treated as 0 for entities in this segment
                </li>
              ))}
            </ul>
          </div>
        )}

        {drift.type_mismatches.length > 0 && (
          <div className="mb-3">
            <div className="text-xs font-semibold text-red-700 uppercase tracking-wide mb-1">
              Type mismatches (these block the upload)
            </div>
            <ul className="text-sm text-slate-700 space-y-0.5">
              {drift.type_mismatches.map((tm) => (
                <li key={tm.name}>
                  <code>{tm.name}</code>: {tm.dataset_dtype} → {tm.segment_dtype}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="mt-5 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
}
