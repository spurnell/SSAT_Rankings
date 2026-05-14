"use client";

import { ChangeEvent, FormEvent, useState } from "react";

interface DatasetUploadFormProps {
  mode: "create" | "append";
  defaultTitle?: string;
  defaultNameColumn?: string;
  knownColumnNames?: string[]; // when appending: name_column is fixed
  submitLabel?: string;
  onSubmit: (args: {
    file: File;
    title?: string;
    name_column?: string;
    segment_label: string;
  }) => Promise<void>;
}

export default function DatasetUploadForm({
  mode,
  defaultTitle = "",
  defaultNameColumn = "",
  knownColumnNames,
  submitLabel,
  onSubmit,
}: DatasetUploadFormProps) {
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState(defaultTitle);
  const [nameColumn, setNameColumn] = useState(defaultNameColumn);
  const [segmentLabel, setSegmentLabel] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function onFileChange(e: ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0] ?? null;
    setFile(f);
    if (f && !title) setTitle(f.name.replace(/\.[^.]+$/, ""));
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) {
      setError("Please choose a CSV or XLSX file.");
      return;
    }
    if (!segmentLabel.trim()) {
      setError("Segment label is required (e.g. '2024 season').");
      return;
    }
    if (mode === "create" && !nameColumn.trim()) {
      setError("Name column is required.");
      return;
    }
    if (mode === "create" && !title.trim()) {
      setError("Dataset title is required.");
      return;
    }
    setSubmitting(true);
    try {
      await onSubmit({
        file,
        title: mode === "create" ? title.trim() : undefined,
        name_column: mode === "create" ? nameColumn.trim() : undefined,
        segment_label: segmentLabel.trim(),
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "upload failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          File (CSV or XLSX)
        </label>
        <input
          type="file"
          accept=".csv,.xlsx,.xlsm"
          onChange={onFileChange}
          className="block w-full text-sm text-slate-700 file:mr-4 file:py-2 file:px-3 file:rounded-md file:border file:border-slate-300 file:bg-white file:text-slate-700 file:text-sm hover:file:bg-slate-50"
        />
        <p className="text-xs text-slate-500 mt-1">
          Max 5 MB, 10,000 rows. Need at least 10 rows, one name column, and
          one numeric column.
        </p>
      </div>

      {mode === "create" && (
        <>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Dataset title
            </label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="My 2024 fantasy season"
              className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              Name column
            </label>
            <input
              type="text"
              value={nameColumn}
              onChange={(e) => setNameColumn(e.target.value)}
              placeholder="player_name"
              className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm"
            />
            <p className="text-xs text-slate-500 mt-1">
              Which column identifies the entity (player, team, etc.). Used
              to match the same entity across future uploads.
            </p>
          </div>
        </>
      )}

      {mode === "append" && knownColumnNames && knownColumnNames.length > 0 && (
        <div className="text-xs text-slate-500">
          Name column for this dataset: <code className="text-slate-700">{defaultNameColumn}</code>
        </div>
      )}

      <div>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Segment label
        </label>
        <input
          type="text"
          value={segmentLabel}
          onChange={(e) => setSegmentLabel(e.target.value)}
          placeholder="2024 season"
          className="w-full rounded-md border border-slate-300 bg-white text-slate-900 px-3 py-2 text-sm"
        />
        <p className="text-xs text-slate-500 mt-1">
          Identifies this upload within the dataset. Must be unique — e.g.
          &quot;2024 season&quot;, &quot;Week 1-9&quot;, etc.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-3 text-red-700 text-sm">
          {error}
        </div>
      )}

      <button
        type="submit"
        disabled={submitting}
        className="px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {submitting ? "Uploading…" : submitLabel ?? "Upload"}
      </button>
    </form>
  );
}
