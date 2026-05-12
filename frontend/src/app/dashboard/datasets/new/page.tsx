"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import DatasetUploadForm from "@/components/custom_data/DatasetUploadForm";
import { useAuth } from "@/contexts/AuthContext";
import { createDataset } from "@/lib/authApi";

export default function NewDatasetPage() {
  const { user, loading: authLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (authLoading) return;
    if (!user) router.replace("/sign-in");
  }, [authLoading, user, router]);

  if (authLoading || !user) {
    return <div className="max-w-3xl mx-auto px-4 py-12 text-slate-500">Loading…</div>;
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-6">
        <Link href="/dashboard/datasets" className="text-sm text-slate-600 hover:text-slate-900">
          ← Back to data uploads
        </Link>
      </div>

      <h1 className="text-2xl font-bold text-slate-900 mb-2">New data upload</h1>
      <p className="text-slate-600 mb-6 text-sm">
        Upload a CSV or XLSX. Once it's created you can append more files later
        as additional segments — useful for ranking across multiple seasons.
      </p>

      <div className="bg-white rounded-lg shadow p-6">
        <DatasetUploadForm
          mode="create"
          submitLabel="Create dataset"
          onSubmit={async ({ file, title, name_column, segment_label }) => {
            const ds = await createDataset({
              file,
              title: title!,
              name_column: name_column!,
              segment_label,
            });
            router.push(`/dashboard/datasets/${ds.id}`);
          }}
        />
      </div>
    </div>
  );
}
