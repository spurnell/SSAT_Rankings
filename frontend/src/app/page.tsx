import Link from "next/link";

export default function Home() {
  return (
    <div className="font-[family-name:var(--font-geist-sans)]">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 to-slate-800 text-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl font-bold mb-6">
              SSAT NFL Player Rankings
            </h1>
            <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
              Data-driven rankings using z-score methodology for fair, position-specific
              player evaluation across all NFL positions. Updated each season based on
              full regular season performance (Weeks 1-18).
            </p>
            <div className="flex gap-4 justify-center">
              <Link
                href="/rankings"
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
              >
                View Rankings
              </Link>
              <Link
                href="/how-it-works"
                className="bg-slate-700 hover:bg-slate-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
              >
                Learn More
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* How We Rank Section */}
      <section className="py-16 bg-slate-50">
        <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-slate-900 mb-6">
            How We Rank Players
          </h2>
          <p className="text-lg text-slate-600 mb-4">
            Our rankings use <span className="font-semibold">z-score normalization</span> to
            compare players fairly within their position group. Each player is evaluated
            on position-specific categories and scored on a <span className="font-semibold">60-100 scale</span> based
            on their <span className="font-semibold">full season statistics</span>.
          </p>
          <Link
            href="/how-it-works"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-semibold transition-colors"
          >
            Learn more about our methodology
            <svg
              className="ml-2 w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </Link>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-blue-600 py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Explore the Rankings?
          </h2>
          <p className="text-blue-100 mb-8">
            Compare players, filter by position, and discover hidden gems.
          </p>
          <Link
            href="/rankings"
            className="bg-white text-blue-600 hover:bg-blue-50 px-8 py-3 rounded-lg font-semibold transition-colors inline-block"
          >
            Get Started
          </Link>
        </div>
      </section>
    </div>
  );
}
