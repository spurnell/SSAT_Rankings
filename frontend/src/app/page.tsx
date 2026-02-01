import Link from "next/link";

export default function Home() {
  return (
    <div className="font-[family-name:var(--font-geist-sans)]">
      {/* Hero Section */}
      <section className="bg-gradient-to-br from-slate-900 to-slate-800 text-white py-20">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="text-center">
            <h1 className="text-4xl sm:text-5xl font-bold mb-6">
              NFL Defensive Player Rankings
            </h1>
            <p className="text-xl text-slate-300 mb-8 max-w-2xl mx-auto">
              Data-driven rankings using advanced z-score methodology to evaluate
              NFL defensive players across multiple statistical categories.
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

      {/* Features Section */}
      <section className="py-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <h2 className="text-3xl font-bold text-center text-slate-900 mb-12">
            How We Rank Players
          </h2>
          <div className="grid md:grid-cols-4 gap-8">
            {[
              {
                title: "Run Defense",
                description: "Tackle efficiency, run stops, and yards allowed metrics",
              },
              {
                title: "Pass Rush",
                description: "Sacks, pressures, and quarterback disruption stats",
              },
              {
                title: "Coverage",
                description: "Pass breakups, interceptions, and completion percentage allowed",
              },
              {
                title: "Playmaking",
                description: "Turnovers forced, big plays, and impact moments",
              },
            ].map((feature) => (
              <div
                key={feature.title}
                className="bg-white p-6 rounded-lg shadow-md hover:shadow-lg transition-shadow"
              >
                <h3 className="text-lg font-semibold text-slate-900 mb-2">
                  {feature.title}
                </h3>
                <p className="text-slate-600">{feature.description}</p>
              </div>
            ))}
          </div>
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
