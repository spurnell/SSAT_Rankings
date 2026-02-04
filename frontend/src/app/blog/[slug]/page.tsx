"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { fetchBlogPost, BlogPost } from "@/lib/api";
import BlogContent from "@/components/blog/BlogContent";

const POST_TYPE_LABELS: Record<string, string> = {
  "power-rankings": "Power Rankings",
  spotlight: "Player Spotlight",
  position: "Position Analysis",
  comparison: "Player Comparison",
};

export default function BlogPostPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [post, setPost] = useState<BlogPost | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadPost() {
      if (!slug) return;

      try {
        const data = await fetchBlogPost(slug);
        setPost(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load post");
      } finally {
        setLoading(false);
      }
    }
    loadPost();
  }, [slug]);

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <div className="animate-pulse">
          <div className="h-4 bg-slate-200 rounded w-1/4 mb-4"></div>
          <div className="h-10 bg-slate-200 rounded w-3/4 mb-6"></div>
          <div className="space-y-3">
            <div className="h-4 bg-slate-200 rounded w-full"></div>
            <div className="h-4 bg-slate-200 rounded w-full"></div>
            <div className="h-4 bg-slate-200 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !post) {
    return (
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
        <Link
          href="/blog"
          className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-8"
        >
          &larr; Back to Blog
        </Link>
        <div className="bg-red-50 text-red-700 p-6 rounded-lg">
          <h2 className="text-xl font-semibold mb-2">Post Not Found</h2>
          <p>{error || "The requested blog post could not be found."}</p>
        </div>
      </div>
    );
  }

  const formattedDate = post.published_at
    ? new Date(post.published_at).toLocaleDateString("en-US", {
        year: "numeric",
        month: "long",
        day: "numeric",
      })
    : "Draft";

  const typeLabel = POST_TYPE_LABELS[post.post_type] || post.post_type;

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
      <Link
        href="/blog"
        className="inline-flex items-center text-blue-600 hover:text-blue-800 mb-8"
      >
        &larr; Back to Blog
      </Link>

      <article>
        <header className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="px-3 py-1 text-sm font-medium bg-blue-100 text-blue-800 rounded">
              {typeLabel}
            </span>
            <span className="text-slate-500">{formattedDate}</span>
          </div>

          <h1 className="text-4xl font-bold text-slate-900 mb-4">{post.title}</h1>

          {post.excerpt && (
            <p className="text-xl text-slate-600 leading-relaxed">{post.excerpt}</p>
          )}

          {post.tags && post.tags.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-4">
              {post.tags.map((tag) => (
                <span
                  key={tag}
                  className="px-2 py-1 text-sm bg-slate-100 text-slate-600 rounded"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}
        </header>

        <hr className="mb-8 border-slate-200" />

        <BlogContent content={post.content} />

        {post.featured_players && post.featured_players.length > 0 && (
          <div className="mt-12 p-4 bg-slate-50 rounded-lg">
            <h3 className="text-sm font-semibold text-slate-700 mb-2">
              Featured Players
            </h3>
            <div className="flex flex-wrap gap-2">
              {post.featured_players.map((player) => (
                <span
                  key={player}
                  className="px-3 py-1 text-sm bg-white border border-slate-200 rounded-full"
                >
                  {player}
                </span>
              ))}
            </div>
          </div>
        )}
      </article>
    </div>
  );
}
