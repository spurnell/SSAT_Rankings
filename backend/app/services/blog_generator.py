"""
Blog generator service using Claude API.
"""
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from anthropic import Anthropic

# Load .env file from backend directory
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(env_path)
from slugify import slugify
from sqlalchemy.orm import Session

from app.db.models import BlogPost
from app.models.blog_schemas import GeneratedPost
from app.services.insights import (
    get_rankings_data,
    get_top_performers,
    get_player_spotlight,
    get_position_breakdown,
    get_player_comparison,
)
from app.core.prompts import (
    SYSTEM_PROMPT,
    get_power_rankings_prompt,
    get_spotlight_prompt,
    get_position_analysis_prompt,
    get_comparison_prompt,
)


def get_anthropic_client() -> Anthropic:
    """Get Anthropic client with API key from environment."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY environment variable is not set")
    return Anthropic(api_key=api_key)


def generate_with_claude(system_prompt: str, user_prompt: str) -> GeneratedPost:
    """Generate content using Claude API."""
    client = get_anthropic_client()

    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[
            {"role": "user", "content": user_prompt}
        ],
    )

    # Extract the text content from the response
    content = response.content[0].text

    # Parse JSON from the response
    try:
        # Find JSON in the response (it might be wrapped in markdown code blocks)
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()
        else:
            json_str = content.strip()

        data = json.loads(json_str)
        return GeneratedPost(
            title=data["title"],
            excerpt=data["excerpt"],
            content=data["content"],
            tags=data.get("tags", []),
        )
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        # If JSON parsing fails, try to extract content directly
        raise ValueError(f"Failed to parse Claude response as JSON: {e}\nResponse: {content[:500]}...")


def generate_power_rankings(
    count: int = 10,
    min_games: int = 8,
    position_group: str = "DEF",
) -> GeneratedPost:
    """Generate a power rankings blog post."""
    rankings = get_rankings_data(min_games, position_group=position_group)
    top_players = get_top_performers(rankings, count, position_group=position_group)

    system_prompt, user_prompt = get_power_rankings_prompt(top_players["players"], position_group=position_group)
    return generate_with_claude(system_prompt, user_prompt)


def generate_player_spotlight(
    player_name: str,
    min_games: int = 8,
) -> GeneratedPost:
    """Generate a player spotlight blog post."""
    rankings = get_rankings_data(min_games)
    insight_data = get_player_spotlight(rankings, player_name)

    if not insight_data["players"]:
        raise ValueError(f"Player '{player_name}' not found in rankings")

    system_prompt, user_prompt = get_spotlight_prompt(insight_data)
    return generate_with_claude(system_prompt, user_prompt)


def generate_position_analysis(
    position: str,
    min_games: int = 8,
) -> GeneratedPost:
    """Generate a position analysis blog post."""
    rankings = get_rankings_data(min_games)
    insight_data = get_position_breakdown(rankings, position.upper())

    if not insight_data["players"]:
        raise ValueError(f"No players found for position '{position}'")

    system_prompt, user_prompt = get_position_analysis_prompt(insight_data)
    return generate_with_claude(system_prompt, user_prompt)


def generate_comparison(
    player1_name: str,
    player2_name: str,
    min_games: int = 8,
) -> GeneratedPost:
    """Generate a player comparison blog post."""
    rankings = get_rankings_data(min_games)
    insight_data = get_player_comparison(rankings, player1_name, player2_name)

    if not insight_data["players"]:
        raise ValueError(f"One or both players not found: {player1_name}, {player2_name}")

    system_prompt, user_prompt = get_comparison_prompt(insight_data)
    return generate_with_claude(system_prompt, user_prompt)


def create_slug(title: str, post_type: str) -> str:
    """Create a unique slug from title and timestamp."""
    base_slug = slugify(title, max_length=50)
    timestamp = datetime.now().strftime("%Y%m%d")
    return f"{base_slug}-{timestamp}"


def save_blog_post(
    db: Session,
    generated: GeneratedPost,
    post_type: str,
    featured_players: Optional[list[str]] = None,
) -> BlogPost:
    """Save a generated blog post to the database."""
    slug = create_slug(generated.title, post_type)

    # Check if slug already exists and append number if needed
    existing = db.query(BlogPost).filter(BlogPost.slug.like(f"{slug}%")).count()
    if existing > 0:
        slug = f"{slug}-{existing + 1}"

    post = BlogPost(
        slug=slug,
        title=generated.title,
        excerpt=generated.excerpt,
        content=generated.content,
        post_type=post_type,
        featured_players=featured_players,
        tags=generated.tags,
        is_published=False,
    )

    db.add(post)
    db.commit()
    db.refresh(post)

    return post


def publish_post(db: Session, slug: str) -> BlogPost:
    """Publish a draft blog post."""
    post = db.query(BlogPost).filter(BlogPost.slug == slug).first()

    if not post:
        raise ValueError(f"Post with slug '{slug}' not found")

    post.is_published = True
    post.published_at = datetime.utcnow()

    db.commit()
    db.refresh(post)

    return post


def unpublish_post(db: Session, slug: str) -> BlogPost:
    """Unpublish a blog post."""
    post = db.query(BlogPost).filter(BlogPost.slug == slug).first()

    if not post:
        raise ValueError(f"Post with slug '{slug}' not found")

    post.is_published = False
    post.published_at = None

    db.commit()
    db.refresh(post)

    return post


def delete_post(db: Session, slug: str) -> bool:
    """Delete a blog post."""
    post = db.query(BlogPost).filter(BlogPost.slug == slug).first()

    if not post:
        raise ValueError(f"Post with slug '{slug}' not found")

    db.delete(post)
    db.commit()

    return True


def list_posts(
    db: Session,
    include_drafts: bool = False,
    limit: int = 50,
) -> list[BlogPost]:
    """List blog posts."""
    query = db.query(BlogPost)

    if not include_drafts:
        query = query.filter(BlogPost.is_published == True)

    return query.order_by(BlogPost.created_at.desc()).limit(limit).all()
