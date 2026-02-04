"""
CLI tool for generating blog posts using Claude API.

Usage:
    python -m app.cli.generate_blog insights
    python -m app.cli.generate_blog generate power-rankings --preview
    python -m app.cli.generate_blog generate spotlight --player "Micah Parsons"
    python -m app.cli.generate_blog generate position --position EDGE
    python -m app.cli.generate_blog generate comparison --player1 "T.J. Watt" --player2 "Myles Garrett"
    python -m app.cli.generate_blog list
    python -m app.cli.generate_blog publish <slug>
"""
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from typing import Optional

from app.db.database import SessionLocal, init_db
from app.services.insights import (
    get_all_insights,
    get_rankings_data,
)
from app.services.blog_generator import (
    generate_power_rankings,
    generate_player_spotlight,
    generate_position_analysis,
    generate_comparison,
    save_blog_post,
    publish_post,
    unpublish_post,
    delete_post,
    list_posts,
)

app = typer.Typer(help="Blog generation CLI for SSAT Rankings")
console = Console()


@app.command()
def insights(
    min_games: int = typer.Option(8, "--min-games", "-g", help="Minimum games played filter"),
):
    """Show available insights from the current rankings data."""
    console.print("\n[bold blue]Fetching rankings data...[/bold blue]")

    try:
        all_insights = get_all_insights(min_games)

        if "error" in all_insights:
            console.print(f"[red]Error: {all_insights['error']}[/red]")
            raise typer.Exit(1)

        console.print(f"\n[green]Total Players:[/green] {all_insights['total_players']}")
        console.print(f"[green]Minimum Games Filter:[/green] {all_insights['min_games_filter']}")
        console.print(f"[green]Available Positions:[/green] {', '.join(all_insights['available_positions'])}")

        console.print("\n[bold]Available Insights:[/bold]")
        for insight in all_insights["insights"]:
            console.print(f"\n  [cyan]{insight['insight_type']}[/cyan]: {insight['title']}")
            console.print(f"    {insight['description']}")
            if insight["players"]:
                console.print(f"    Players: {len(insight['players'])}")

    except Exception as e:
        console.print(f"[red]Error fetching insights: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def generate(
    post_type: str = typer.Argument(..., help="Type of post: power-rankings, spotlight, position, comparison"),
    preview: bool = typer.Option(False, "--preview", "-p", help="Preview without saving"),
    player: Optional[str] = typer.Option(None, "--player", help="Player name for spotlight"),
    player1: Optional[str] = typer.Option(None, "--player1", help="First player for comparison"),
    player2: Optional[str] = typer.Option(None, "--player2", help="Second player for comparison"),
    position: Optional[str] = typer.Option(None, "--position", help="Position for position analysis"),
    position_group: str = typer.Option("DEF", "--group", help="Position group: DEF, QB, RB, WR, TE, K"),
    count: int = typer.Option(10, "--count", "-c", help="Number of players for power rankings"),
    min_games: int = typer.Option(8, "--min-games", "-g", help="Minimum games played filter"),
):
    """Generate a blog post using Claude API."""
    init_db()

    console.print(f"\n[bold blue]Generating {post_type} blog post for {position_group}...[/bold blue]")

    try:
        if post_type == "power-rankings":
            generated = generate_power_rankings(count=count, min_games=min_games, position_group=position_group)
            featured_players = None

        elif post_type == "spotlight":
            if not player:
                console.print("[red]Error: --player is required for spotlight posts[/red]")
                raise typer.Exit(1)
            generated = generate_player_spotlight(player_name=player, min_games=min_games)
            featured_players = [player]

        elif post_type == "position":
            if not position:
                console.print("[red]Error: --position is required for position analysis posts[/red]")
                raise typer.Exit(1)
            generated = generate_position_analysis(position=position, min_games=min_games)
            featured_players = None

        elif post_type == "comparison":
            if not player1 or not player2:
                console.print("[red]Error: --player1 and --player2 are required for comparison posts[/red]")
                raise typer.Exit(1)
            generated = generate_comparison(
                player1_name=player1,
                player2_name=player2,
                min_games=min_games,
            )
            featured_players = [player1, player2]

        else:
            console.print(f"[red]Unknown post type: {post_type}[/red]")
            console.print("Valid types: power-rankings, spotlight, position, comparison")
            raise typer.Exit(1)

        # Display the generated content
        console.print(Panel(f"[bold green]{generated.title}[/bold green]"))
        console.print(f"\n[yellow]Excerpt:[/yellow] {generated.excerpt}")
        console.print(f"[yellow]Tags:[/yellow] {', '.join(generated.tags)}")
        console.print("\n[bold]Content Preview:[/bold]")
        console.print(Markdown(generated.content[:2000] + "..." if len(generated.content) > 2000 else generated.content))

        if preview:
            console.print("\n[dim]Preview mode - post not saved[/dim]")
        else:
            # Save to database
            db = SessionLocal()
            try:
                post = save_blog_post(
                    db=db,
                    generated=generated,
                    post_type=post_type,
                    featured_players=featured_players,
                )
                console.print(f"\n[green]Post saved![/green]")
                console.print(f"  Slug: [cyan]{post.slug}[/cyan]")
                console.print(f"  Status: [yellow]Draft[/yellow]")
                console.print(f"\nTo publish: [dim]python -m app.cli.generate_blog publish {post.slug}[/dim]")
            finally:
                db.close()

    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error generating post: {e}[/red]")
        import traceback
        traceback.print_exc()
        raise typer.Exit(1)


@app.command("list")
def list_all(
    drafts: bool = typer.Option(False, "--drafts", "-d", help="Include draft posts"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum posts to show"),
):
    """List all blog posts."""
    init_db()

    db = SessionLocal()
    try:
        posts = list_posts(db, include_drafts=drafts, limit=limit)

        if not posts:
            console.print("\n[yellow]No posts found.[/yellow]")
            return

        table = Table(title="Blog Posts")
        table.add_column("Slug", style="cyan")
        table.add_column("Title", style="white")
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Created", style="dim")

        for post in posts:
            status = "[green]Published[/green]" if post.is_published else "[yellow]Draft[/yellow]"
            created = post.created_at.strftime("%Y-%m-%d %H:%M") if post.created_at else "N/A"
            table.add_row(
                post.slug,
                post.title[:40] + "..." if len(post.title) > 40 else post.title,
                post.post_type,
                status,
                created,
            )

        console.print(table)

    finally:
        db.close()


@app.command()
def publish(
    slug: str = typer.Argument(..., help="Slug of the post to publish"),
):
    """Publish a draft blog post."""
    init_db()

    db = SessionLocal()
    try:
        post = publish_post(db, slug)
        console.print(f"\n[green]Published![/green] {post.title}")
        console.print(f"  URL: /blog/{post.slug}")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def unpublish(
    slug: str = typer.Argument(..., help="Slug of the post to unpublish"),
):
    """Unpublish a blog post (convert to draft)."""
    init_db()

    db = SessionLocal()
    try:
        post = unpublish_post(db, slug)
        console.print(f"\n[yellow]Unpublished![/yellow] {post.title}")
        console.print("  Status: Draft")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def delete(
    slug: str = typer.Argument(..., help="Slug of the post to delete"),
    force: bool = typer.Option(False, "--force", "-f", help="Skip confirmation"),
):
    """Delete a blog post."""
    init_db()

    if not force:
        confirm = typer.confirm(f"Are you sure you want to delete post '{slug}'?")
        if not confirm:
            console.print("[dim]Cancelled[/dim]")
            return

    db = SessionLocal()
    try:
        delete_post(db, slug)
        console.print(f"\n[red]Deleted![/red] {slug}")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
    finally:
        db.close()


@app.command()
def show(
    slug: str = typer.Argument(..., help="Slug of the post to show"),
):
    """Show full content of a blog post."""
    init_db()

    db = SessionLocal()
    try:
        from app.db.models import BlogPost
        post = db.query(BlogPost).filter(BlogPost.slug == slug).first()

        if not post:
            console.print(f"[red]Post not found: {slug}[/red]")
            raise typer.Exit(1)

        console.print(Panel(f"[bold]{post.title}[/bold]"))
        console.print(f"[dim]Type: {post.post_type} | Status: {'Published' if post.is_published else 'Draft'}[/dim]")
        console.print(f"[dim]Created: {post.created_at}[/dim]")
        if post.tags:
            console.print(f"[dim]Tags: {', '.join(post.tags)}[/dim]")
        console.print("\n")
        console.print(Markdown(post.content))

    finally:
        db.close()


if __name__ == "__main__":
    app()
