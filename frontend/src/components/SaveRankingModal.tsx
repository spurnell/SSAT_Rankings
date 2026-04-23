"use client";

import { FormEvent, useState } from "react";

export type ShareMode = "none" | "live" | "frozen";

interface Props {
  open: boolean;
  onClose: () => void;
  onSubmit: (values: { title: string; share_mode: ShareMode }) => Promise<void>;
}

export default function SaveRankingModal({ open, onClose, onSubmit }: Props) {
  const [title, setTitle] = useState("");
  const [shareMode, setShareMode] = useState<ShareMode>("none");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!open) return null;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await onSubmit({ title: title.trim(), share_mode: shareMode });
      setTitle("");
      setShareMode("none");
    } catch (err) {
      setError(err instanceof Error ? err.message : "save failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-lg shadow-xl w-full max-w-md mx-4 p-6"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 className="text-xl font-semibold text-slate-900 mb-4">Save ranking</h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="text-sm font-medium text-slate-700">Title</span>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              maxLength={200}
              placeholder="e.g. My DEF rankings — Week 12"
              className="mt-1 block w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </label>

          <fieldset className="space-y-2">
            <legend className="text-sm font-medium text-slate-700">Share</legend>
            {(
              [
                { v: "none", t: "Private", d: "Only visible to you." },
                { v: "live", t: "Live share", d: "Public URL. Recomputes each view as data updates." },
                { v: "frozen", t: "Frozen snapshot", d: "Public URL. Locks today's numbers — future data changes won't affect it." },
              ] as { v: ShareMode; t: string; d: string }[]
            ).map((opt) => (
              <label key={opt.v} className="flex items-start gap-3 rounded-md border border-slate-200 p-3 cursor-pointer hover:bg-slate-50">
                <input
                  type="radio"
                  name="share_mode"
                  value={opt.v}
                  checked={shareMode === opt.v}
                  onChange={() => setShareMode(opt.v)}
                  className="mt-1"
                />
                <div>
                  <div className="text-sm font-medium text-slate-900">{opt.t}</div>
                  <div className="text-xs text-slate-600">{opt.d}</div>
                </div>
              </label>
            ))}
          </fieldset>

          {error && <p className="text-sm text-red-600">{error}</p>}

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-slate-700 bg-white border border-slate-300 rounded-md hover:bg-slate-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !title.trim()}
              className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
            >
              {submitting ? "Saving…" : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
