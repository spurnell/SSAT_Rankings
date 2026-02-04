import Link from "next/link";
import { BlogPostListItem } from "@/lib/api";

interface BlogCardProps {
  post: BlogPostListItem;
}

const POST_TYPE_LABELS: Record<string, string> = {
  "power-rankings": "Power Rankings",
  spotlight: "Player Spotlight",
  position: "Position Analysis",
  comparison: "Player Comparison",
};

const POST_TYPE_COLORS: Record<string, string> = {
  "power-rankings": "bg-blue-100 text-blue-800",
  spotlight: "bg-purple-100 text-purple-800",
  position: "bg-green-100 text-green-800",
  comparison: "bg-orange-100 text-orange-800",
};

export default function BlogCard({ post }: BlogCardProps) {
  const formattedDate = post.published_at
    ? new Date(post.published_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "Draft";

  const typeLabel = POST_TYPE_LABELS[post.post_type] || post.post_type;
  const typeColor = POST_TYPE_COLORS[post.post_type] || "bg-gray-100 text-gray-800";

  return (
    <article className="bg-white p-6 rounded-lg shadow hover:shadow-md transition-shadow">
      <div className="flex items-center gap-3 mb-3">
        <span className={`px-2 py-1 text-xs font-medium rounded ${typeColor}`}>
          {typeLabel}
        </span>
        <span className="text-sm text-slate-500">{formattedDate}</span>
      </div>

      <Link href={`/blog/${post.slug}`}>
        <h2 className="text-xl font-semibold text-slate-900 mb-2 hover:text-blue-600 transition-colors">
          {post.title}
        </h2>
      </Link>

      {post.excerpt && (
        <p className="text-slate-600 mb-4">{post.excerpt}</p>
      )}

      {post.tags && post.tags.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {post.tags.map((tag) => (
            <span
              key={tag}
              className="px-2 py-1 text-xs bg-slate-100 text-slate-600 rounded"
            >
              {tag}
            </span>
          ))}
        </div>
      )}

      <Link
        href={`/blog/${post.slug}`}
        className="inline-block mt-4 text-blue-600 hover:text-blue-800 text-sm font-medium"
      >
        Read more &rarr;
      </Link>
    </article>
  );
}
