"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface NewRankingChooserModalProps {
  open: boolean;
  onClose: () => void;
}

export default function NewRankingChooserModal({
  open,
  onClose,
}: NewRankingChooserModalProps) {
  const router = useRouter();

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 px-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="bg-white rounded-xl shadow-xl max-w-2xl w-full p-6 sm:p-8"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              How do you want to start?
            </h2>
            <p className="text-sm text-slate-600 mt-1">
              Pick a ranking style — you can always create another one.
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-slate-400 hover:text-slate-700 text-xl leading-none px-2"
          >
            ×
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <button
            onClick={() => {
              router.push("/rankings/custom");
              onClose();
            }}
            className="text-left rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50 transition p-5 group"
          >
            <div className="text-base font-semibold text-slate-900 group-hover:text-blue-700">
              Use our categories
            </div>
            <div className="text-sm text-slate-600 mt-2">
              Adjust the weights of our pre-built categories. Fastest way to
              tune a ranking.
            </div>
          </button>

          <button
            onClick={() => {
              router.push("/rankings/custom/build");
              onClose();
            }}
            className="text-left rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50 transition p-5 group"
          >
            <div className="text-base font-semibold text-slate-900 group-hover:text-blue-700">
              Create my own categories
            </div>
            <div className="text-sm text-slate-600 mt-2">
              Pick stats yourself (including PFF) and group them into up to 5
              sub-categories with custom weights.
            </div>
          </button>

          <button
            onClick={() => {
              router.push("/dashboard/datasets/new");
              onClose();
            }}
            className="text-left rounded-lg border border-slate-200 hover:border-blue-500 hover:bg-blue-50 transition p-5 group"
          >
            <div className="text-base font-semibold text-slate-900 group-hover:text-blue-700">
              Upload your own data
            </div>
            <div className="text-sm text-slate-600 mt-2">
              CSV or XLSX. Append more files later as additional segments and
              rank across them.
            </div>
          </button>
        </div>
      </div>
    </div>
  );
}
