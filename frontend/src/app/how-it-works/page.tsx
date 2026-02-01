export default function HowItWorksPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">How It Works</h1>

      <div className="prose prose-slate max-w-none">
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Z-Score Methodology
          </h2>
          <p className="text-slate-600 mb-4">
            Our ranking system uses z-scores to normalize player statistics across
            different categories. A z-score measures how many standard deviations
            a value is from the mean, allowing us to compare players fairly
            regardless of the scale of different stats.
          </p>
          <div className="bg-slate-100 p-4 rounded-lg font-mono text-sm">
            z = (x - μ) / σ
          </div>
          <p className="text-slate-500 text-sm mt-2">
            Where x is the player&apos;s stat, μ is the mean, and σ is the standard
            deviation
          </p>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Statistical Categories
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            {[
              {
                title: "Run Defense",
                stats: ["Tackles", "Solo Tackles", "Run Stops", "Missed Tackle %"],
              },
              {
                title: "Pass Rush",
                stats: ["Sacks", "QB Hits", "Pressures", "Pass Rush Win Rate"],
              },
              {
                title: "Coverage",
                stats: [
                  "Pass Breakups",
                  "Interceptions",
                  "Yards Allowed",
                  "Completion % Allowed",
                ],
              },
              {
                title: "Playmaking",
                stats: [
                  "Forced Fumbles",
                  "Fumble Recoveries",
                  "Defensive TDs",
                  "Turnovers",
                ],
              },
            ].map((category) => (
              <div key={category.title} className="bg-white p-6 rounded-lg shadow">
                <h3 className="font-semibold text-slate-900 mb-3">
                  {category.title}
                </h3>
                <ul className="space-y-1">
                  {category.stats.map((stat) => (
                    <li key={stat} className="text-slate-600 text-sm">
                      • {stat}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Weighted Aggregation
          </h2>
          <p className="text-slate-600 mb-4">
            Each category&apos;s z-scores are combined using configurable weights to
            produce a final composite score. By default, all categories are
            weighted equally, but this can be adjusted based on positional
            importance.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Score Rescaling
          </h2>
          <p className="text-slate-600">
            Final scores are rescaled to a 60-100 range for easier interpretation.
            A score of 80 represents an average player, with higher scores
            indicating above-average performance and lower scores indicating
            below-average performance.
          </p>
        </section>
      </div>
    </div>
  );
}
