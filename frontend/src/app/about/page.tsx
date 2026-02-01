export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">About SSAT Rankings</h1>

      <div className="prose prose-slate max-w-none">
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">Our Mission</h2>
          <p className="text-slate-600 mb-4">
            SSAT Rankings aims to provide objective, data-driven evaluations of NFL
            defensive players. By using statistical analysis rather than subjective
            opinions, we help fans, analysts, and fantasy players make more informed
            decisions.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">
            Why Z-Scores?
          </h2>
          <p className="text-slate-600 mb-4">
            Traditional stats can be misleading. A player with 100 tackles might seem
            better than one with 80, but what if they played more games? What if their
            team faced more running plays? Z-scores normalize these differences,
            telling you how a player compares to their peers in context.
          </p>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">Data Sources</h2>
          <p className="text-slate-600 mb-4">
            We aggregate data from multiple reliable sources including official NFL
            statistics and advanced metrics providers. Our database is updated
            regularly throughout the season to provide the most current rankings.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">Contact</h2>
          <p className="text-slate-600">
            Have questions or suggestions? We&apos;d love to hear from you. Reach out to
            us for feedback, partnership opportunities, or just to discuss NFL
            defense.
          </p>
        </section>
      </div>
    </div>
  );
}
