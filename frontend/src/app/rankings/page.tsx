import RankingsTable from "@/components/RankingsTable";

export default function RankingsPage() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-slate-900">NFL Player Rankings by Season</h1>
        <p className="text-slate-600 mt-2">
          Evaluate and compare NFL players across position groups using z-score methodology.
          Select up to two players to compare their category scores and detailed stats.
        </p>
      </div>
      <RankingsTable />
    </div>
  );
}
