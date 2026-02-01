export default function BlogPage() {
  const posts = [
    {
      title: "Understanding Defensive Player Metrics",
      date: "Coming Soon",
      excerpt:
        "A deep dive into the statistics that matter most when evaluating NFL defenders.",
    },
    {
      title: "2024 Season Preview: Top Defensive Prospects",
      date: "Coming Soon",
      excerpt:
        "Breaking down the defensive players to watch heading into the new season.",
    },
    {
      title: "The Evolution of Pass Rush Analytics",
      date: "Coming Soon",
      excerpt:
        "How advanced metrics have changed the way we evaluate edge rushers.",
    },
  ];

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <h1 className="text-3xl font-bold text-slate-900 mb-8">Blog</h1>

      <div className="space-y-8">
        {posts.map((post) => (
          <article
            key={post.title}
            className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow"
          >
            <div className="text-sm text-slate-500 mb-2">{post.date}</div>
            <h2 className="text-xl font-semibold text-slate-900 mb-2">
              {post.title}
            </h2>
            <p className="text-slate-600">{post.excerpt}</p>
          </article>
        ))}
      </div>

      <div className="mt-12 text-center text-slate-500">
        <p>More articles coming soon. Check back for updates!</p>
      </div>
    </div>
  );
}
