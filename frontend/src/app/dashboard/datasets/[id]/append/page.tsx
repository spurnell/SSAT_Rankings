"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";

import DatasetUploadForm from "@/components/custom_data/DatasetUploadForm";
import SchemaDriftModal from "@/components/custom_data/SchemaDriftModal";
import { useAuth } from "@/contexts/AuthContext";
import {
  DatasetDetail,
  SchemaDrift,
  appendSegment,
  getDataset,
} from "@/lib/authApi";

export default function AppendSegmentPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();
  const params = useParams<{ id: string }>();
  const datasetId = Number(params.id);

  const [dataset, setDataset] = useState<DatasetDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [drift, setDrift] = useState<SchemaDrift | null>(null);

  useEffect(() => {
    if (authLoading) return;
    if (!user) router.replace("/sign-in");
  }, [authLoading, user, router]);

  useEffect(() => {
    if (!user || !datasetId) return;
    getDataset(datasetId)
      .then(setDataset)
      .catch((err) => setError(err instanceof Error ? err.message : "failed"));
  }, [user, datasetId]);

  if (authLoading || !user) {
    return <div className="max-w-3xl mx-auto px-4 py-12 text-slate-500">Loading…</div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-4">
        <Link
          href={`/dashboard/datasets/${datasetId}`}
          className="text-sm text-slate-600 hover:text-slate-900"
        >
          ← Back to dataset
        </Link>
      </div>

      <h1 className="text-2xl font-bold text-slate-900 mb-2">Append a segment</h1>
      <p className="text-slate-600 mb-6 text-sm">
        Add another upload to <span className="font-medium">{dataset?.title}</span>.
        The new file should use the same name column. Extra columns will be
        added to the dataset; missing columns will read as null for entities
        in this segment.
      </p>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-red-600 text-sm">
          {error}
        </div>
      )}

      {dataset && (
        <div className="bg-white rounded-lg shadow p-6">
          <DatasetUploadForm
            mode="append"
            defaultNameColumn={dataset.name_column}
            knownColumnNames={dataset.column_schema.map((c) => c.name)}
            submitLabel="Append segment"
            onSubmit={async ({ file, segment_label }) => {
              const res = await appendSegment({
                dataset_id: datasetId,
                file,
                segment_label,
                on_drift: "accept",
              });
              if (
                res.drift.added.length ||
                res.drift.missing.length ||
                res.drift.type_mismatches.length
              ) {
                setDrift(res.drift);
              } else {
                router.push(`/dashboard/datasets/${datasetId}`);
              }
            }}
          />
        </div>
      )}

      {drift && (
        <SchemaDriftModal
          drift={drift}
          onClose={() => {
            setDrift(null);
            router.push(`/dashboard/datasets/${datasetId}`);
          }}
        />
      )}
    </div>
  );
}
