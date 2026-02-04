export default function HowItWorksPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      {/* Hero Section */}
      <section className="mb-16 text-center">
        <h1 className="text-4xl font-bold text-slate-900 mb-4">
          How SSAT Rankings Work
        </h1>
        <p className="text-xl text-slate-600 max-w-2xl mx-auto">
          The Standardized Statistical Assessment Tool (SSAT) creates fair,
          comparable rankings across all NFL positions using statistical
          normalization and position-specific evaluation criteria.
        </p>
      </section>

      <div className="space-y-16">
        {/* Section 1: Core Methodology */}
        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            The Core Methodology: Z-Score Normalization
          </h2>
          <p className="text-slate-600 mb-6">
            At the heart of SSAT is the z-score, a statistical measure that tells
            us how far a player&apos;s performance deviates from the average. This
            allows us to compare players fairly, even when raw statistics have
            vastly different scales.
          </p>
          <div className="bg-slate-100 p-6 rounded-lg mb-4">
            <div className="font-mono text-lg text-center text-slate-900 mb-4">
              z = (x - μ) / σ
            </div>
            <div className="text-sm text-slate-600 space-y-2">
              <p>
                <span className="font-mono font-semibold">x</span> = player&apos;s
                raw statistic
              </p>
              <p>
                <span className="font-mono font-semibold">μ</span> = mean
                (average) across all players at that position
              </p>
              <p>
                <span className="font-mono font-semibold">σ</span> = standard
                deviation (spread of the data)
              </p>
            </div>
          </div>
          <p className="text-slate-600">
            A z-score of <span className="font-semibold">+1</span> means the
            player is one standard deviation above average. A z-score of{" "}
            <span className="font-semibold">-1</span> means one standard deviation
            below. This normalization is applied to every statistic we track.
          </p>
        </section>

        {/* Section 2: Position-Based Categories */}
        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Position-Specific Categories
          </h2>
          <p className="text-slate-600 mb-6">
            Each position is evaluated using categories tailored to their role.
            This ensures quarterbacks are judged on passing efficiency, running
            backs on rushing production, and so on.
          </p>
          <div className="grid md:grid-cols-2 gap-4">
            {[
              {
                position: "QB",
                categories: ["Efficiency", "Volume", "Playmaking", "Ball Security"],
              },
              {
                position: "RB",
                categories: ["Efficiency", "Volume", "Scoring", "Receiving"],
              },
              {
                position: "WR",
                categories: ["Efficiency", "Volume", "Scoring", "Playmaking"],
              },
              {
                position: "TE",
                categories: ["Efficiency", "Volume", "Scoring", "Blocking"],
              },
              {
                position: "Defense",
                categories: ["Run Defense", "Pass Rush", "Coverage", "Playmaking"],
              },
            ].map((item) => (
              <div
                key={item.position}
                className="bg-white p-4 rounded-lg border border-slate-200"
              >
                <span className="inline-block bg-slate-900 text-white text-sm font-semibold px-2 py-1 rounded mb-2">
                  {item.position}
                </span>
                <div className="text-slate-600 text-sm">
                  {item.categories.join(" • ")}
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* Section 3: Category Scoring */}
        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Category-Based Scoring
          </h2>
          <p className="text-slate-600 mb-6">
            Within each category, we average the z-scores of all relevant
            statistics to produce a single category score. Then, categories are
            combined using weights to create an overall score.
          </p>
          <div className="bg-slate-100 p-6 rounded-lg space-y-6">
            <div>
              <div className="text-sm text-slate-500 mb-2">
                Category Score (average of stat z-scores):
              </div>
              <div className="font-mono text-lg text-slate-900">
                Category = (z₁ + z₂ + ... + zₙ) / n
              </div>
            </div>
            <div className="border-t border-slate-300 pt-4">
              <div className="text-sm text-slate-500 mb-2">
                Overall Score (weighted sum of categories):
              </div>
              <div className="font-mono text-lg text-slate-900">
                Overall = w₁×Cat₁ + w₂×Cat₂ + ... + wₖ×Catₖ
              </div>
            </div>
          </div>
          <p className="text-slate-500 text-sm mt-4">
            Weights (w) can be adjusted to emphasize different aspects of
            performance. By default, all categories are weighted equally.
          </p>
        </section>

        {/* Section 4: Score Normalization */}
        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Final Score: The 60-100 Scale
          </h2>
          <p className="text-slate-600 mb-6">
            Raw z-scores are transformed to an intuitive 60-100 scale using linear
            interpolation. This makes scores easy to interpret at a glance.
          </p>
          <div className="bg-slate-100 p-6 rounded-lg mb-6">
            <div className="font-mono text-lg text-center text-slate-900 mb-4">
              Final = 60 + ((raw - min) / (max - min)) × 40
            </div>
            <div className="text-sm text-slate-600 space-y-2">
              <p>
                <span className="font-mono font-semibold">raw</span> = player&apos;s
                weighted composite z-score
              </p>
              <p>
                <span className="font-mono font-semibold">min, max</span> = lowest
                and highest composite scores among all players
              </p>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 text-center max-w-md mx-auto">
            <div className="bg-white p-4 rounded-lg border border-slate-200">
              <div className="text-3xl font-bold text-slate-400">60</div>
              <div className="text-sm text-slate-500">Lowest performer</div>
            </div>
            <div className="bg-white p-4 rounded-lg border border-slate-200">
              <div className="text-3xl font-bold text-slate-900">100</div>
              <div className="text-sm text-slate-500">Top performer</div>
            </div>
          </div>
        </section>

        {/* Section 5: Why SSAT Works */}
        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-6">
            Why SSAT Works
          </h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-100">
              <div className="text-lg font-semibold text-slate-900 mb-2">
                Fair Comparison
              </div>
              <p className="text-slate-600 text-sm">
                Z-scores normalize across different stat scales. Whether it&apos;s
                passing yards (thousands) or touchdowns (dozens), every stat is
                converted to a common scale.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-100">
              <div className="text-lg font-semibold text-slate-900 mb-2">
                Position-Aware
              </div>
              <p className="text-slate-600 text-sm">
                Each position has its own relevant categories and weights. A
                quarterback&apos;s value isn&apos;t measured the same way as a
                linebacker&apos;s.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-100">
              <div className="text-lg font-semibold text-slate-900 mb-2">
                Handles Outliers
              </div>
              <p className="text-slate-600 text-sm">
                For statistics with extreme outliers (like touchdowns), we apply
                log-scaling before z-score calculation to prevent a single stat
                from dominating.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg shadow-sm border border-slate-100">
              <div className="text-lg font-semibold text-slate-900 mb-2">
                Transparent
              </div>
              <p className="text-slate-600 text-sm">
                No black box. Every step of the methodology is documented here.
                You can see exactly how scores are calculated and why players rank
                where they do.
              </p>
            </div>
          </div>
        </section>

        {/* Section 6: Visual Example */}
        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-6">
            Example: From Raw Stats to Final Score
          </h2>
          <div className="bg-slate-50 p-6 rounded-lg border border-slate-200">
            <div className="flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="text-center p-4">
                <div className="text-sm text-slate-500 mb-1">Raw Stats</div>
                <div className="font-mono text-sm text-slate-700">
                  4,200 yds
                  <br />
                  32 TD
                  <br />8 INT
                </div>
              </div>
              <div className="text-2xl text-slate-400">→</div>
              <div className="text-center p-4">
                <div className="text-sm text-slate-500 mb-1">Z-Scores</div>
                <div className="font-mono text-sm text-slate-700">
                  +1.2
                  <br />
                  +0.8
                  <br />
                  -0.3
                </div>
              </div>
              <div className="text-2xl text-slate-400">→</div>
              <div className="text-center p-4">
                <div className="text-sm text-slate-500 mb-1">Category Avg</div>
                <div className="font-mono text-sm text-slate-700">+0.57</div>
              </div>
              <div className="text-2xl text-slate-400">→</div>
              <div className="text-center p-4">
                <div className="text-sm text-slate-500 mb-1">Final Score</div>
                <div className="text-3xl font-bold text-slate-900">87</div>
              </div>
            </div>
            <p className="text-slate-500 text-sm text-center mt-4">
              This simplified example shows how a QB&apos;s passing stats flow through
              the SSAT pipeline.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
