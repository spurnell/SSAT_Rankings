from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class BlogPostBase(BaseModel):
    title: str
    excerpt: Optional[str] = None
    content: str
    post_type: str
    featured_players: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class BlogPostCreate(BlogPostBase):
    slug: str


class BlogPostResponse(BlogPostBase):
    id: int
    slug: str
    published_at: Optional[datetime] = None
    created_at: datetime
    is_published: bool

    class Config:
        from_attributes = True


class BlogPostListItem(BaseModel):
    id: int
    slug: str
    title: str
    excerpt: Optional[str] = None
    post_type: str
    featured_players: Optional[list[str]] = None
    tags: Optional[list[str]] = None
    published_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InsightData(BaseModel):
    """Data structure for insights that will be used for blog generation."""
    insight_type: str
    title: str
    description: str
    players: list[dict]
    stats: Optional[dict] = None


class GeneratedPost(BaseModel):
    """Response from Claude API for blog generation."""
    title: str
    excerpt: str
    content: str
    tags: list[str]
