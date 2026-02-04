import RankingsTable from "@/components/RankingsTable";

export default function RankingsPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">Player Rankings</h1>
        <p className="text-slate-600 mt-2">
          NFL player rankings based on z-score methodology
        </p>
      </div>
      <RankingsTable />
    </div>
  );
}
