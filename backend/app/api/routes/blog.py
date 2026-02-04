from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import BlogPost
from app.models.blog_schemas import BlogPostResponse, BlogPostListItem

router = APIRouter()


@router.get("/blog/posts", response_model=list[BlogPostListItem])
async def list_posts(
    limit: int = 20,
    offset: int = 0,
    post_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """List all published blog posts."""
    query = db.query(BlogPost).filter(BlogPost.is_published == True)

    if post_type:
        query = query.filter(BlogPost.post_type == post_type)

    posts = (
        query
        .order_by(BlogPost.published_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return posts


@router.get("/blog/posts/{slug}", response_model=BlogPostResponse)
async def get_post(slug: str, db: Session = Depends(get_db)):
    """Get a single blog post by slug."""
    post = db.query(BlogPost).filter(BlogPost.slug == slug).first()

    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    if not post.is_published:
        raise HTTPException(status_code=404, detail="Post not found")

    return post
