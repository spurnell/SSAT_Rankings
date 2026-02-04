import Link from "next/link";

export default function AboutPage() {
  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">About SSAT Rankings</h1>

      <div className="prose prose-slate max-w-none">
        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">Our Mission</h2>
          <p className="text-slate-600 mb-4">
            SSAT Rankings aims to provide objective, data-driven evaluations of NFL
            players across all positions. By using statistical analysis and our patented
            z-score methodology rather than subjective opinions, we help fans, analysts,
            and fantasy players make more informed decisions.
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
          <Link
            href="/how-it-works"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
          >
            Learn more about our methodology
            <svg className="ml-1 w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">Our Team</h2>
          <div className="grid md:grid-cols-2 gap-6">
            <div className="bg-white p-6 rounded-lg border border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Spence Purnell</h3>
              <p className="text-sm text-blue-600 mb-3">Co-Founder</p>
              <p className="text-slate-600 text-sm">
                Former Division 1 NCAA basketball player at Stetson University and professional
                rugby player for organizations including Atavus, The Glendale Raptors, and
                Denver Barbarians 7s Rugby. Currently works as a data scientist and author.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-slate-200">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Craig Montgomery</h3>
              <p className="text-sm text-blue-600 mb-3">Co-Founder</p>
              <p className="text-slate-600 text-sm">
                Former Division 1 football player at Georgetown University, now a professional
                long snapping coach operating{" "}
                <a
                  href="https://montgomerylongsnapping.com"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline"
                >
                  montgomerylongsnapping.com
                </a>.
              </p>
            </div>
            <div className="bg-white p-6 rounded-lg border border-slate-200 md:col-span-2">
              <h3 className="text-lg font-semibold text-slate-900 mb-2">Ray Farmer</h3>
              <p className="text-sm text-blue-600 mb-3">Investor</p>
              <p className="text-slate-600 text-sm">
                Former NFL executive and linebacker who played college football at Duke and
                professionally with the Philadelphia Eagles. He held scouting and administrative
                roles with the Atlanta Falcons and Kansas City Chiefs, and served as General
                Manager of the Cleveland Browns from 2014-2015.
              </p>
            </div>
          </div>
        </section>

        <section className="mb-12">
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">Data Sources</h2>
          <p className="text-slate-600 mb-4">
            We aggregate data from multiple reliable sources including official NFL
            statistics and advanced metrics providers. Our database is updated
            regularly throughout the season to provide the most current rankings.
          </p>
          <p className="text-slate-500 text-sm">
            All data rights reserved.
          </p>
        </section>

        <section>
          <h2 className="text-2xl font-semibold text-slate-800 mb-4">Contact</h2>
          <p className="text-slate-600 mb-4">
            Have questions or suggestions? We&apos;d love to hear from you.
          </p>
          <div className="bg-slate-50 p-6 rounded-lg space-y-3">
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
              <a href="mailto:spence.purnell@gmail.com" className="text-blue-600 hover:underline">
                spence.purnell@gmail.com
              </a>
            </div>
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 5a2 2 0 012-2h3.28a1 1 0 01.948.684l1.498 4.493a1 1 0 01-.502 1.21l-2.257 1.13a11.042 11.042 0 005.516 5.516l1.13-2.257a1 1 0 011.21-.502l4.493 1.498a1 1 0 01.684.949V19a2 2 0 01-2 2h-1C9.716 21 3 14.284 3 6V5z" />
              </svg>
              <a href="tel:941-256-5362" className="text-blue-600 hover:underline">
                941-256-5362
              </a>
            </div>
            <div className="flex items-center gap-3">
              <svg className="w-5 h-5 text-slate-500" fill="currentColor" viewBox="0 0 24 24">
                <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
              </svg>
              <a
                href="https://twitter.com/SportSSATranks"
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:underline"
              >
                @SportSSATranks
              </a>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
}
