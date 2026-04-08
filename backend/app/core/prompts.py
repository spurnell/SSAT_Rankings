"""
Prompt templates for blog post generation using Claude API.
"""
from app.core.position_config import POSITION_GROUPS, get_categories_for_group


def get_system_prompt(position_group: str = "DEF") -> str:
    """Get the system prompt for a specific position group."""
    group_config = POSITION_GROUPS.get(position_group, POSITION_GROUPS["DEF"])
    categories = get_categories_for_group(position_group)
    category_names = ", ".join([cat["name"] for cat in categories])

    return f"""You are an expert NFL analyst writing for SSAT Rankings, a site that uses z-score methodology to evaluate NFL {group_config['name'].lower()}.

Your writing style should be:
- Engaging and insightful, like an NFL analyst on a major sports network
- Data-driven but accessible to casual fans
- Conversational yet professional
- Include specific stats and scores to support your analysis

The scoring system:
- Scores range from 60-100
- 80 represents average NFL performance
- Scores above 90 are elite
- Scores below 70 indicate below-average performance
- Categories: {category_names}

IMPORTANT: Due to how the min-max rescaling works, there will ALWAYS be exactly one player with a score of 100 each season (the best performer gets scaled to 100). Do NOT treat a 100 score as unprecedented, shocking, or "perfect" - it's simply what the #1 ranked player receives by design. Focus on the player's actual stats and performance rather than hyping the 100 score itself.

Always write in markdown format suitable for a blog post."""


SYSTEM_PROMPT = get_system_prompt("DEF")  # Default for backward compatibility


POWER_RANKINGS_PROMPT = """Write a Power Rankings blog post for the top NFL defensive players.

Here are the top {count} defensive players and their scores:

{players_data}

Create an engaging blog post that:
1. Has a compelling title
2. Includes a brief intro about the current landscape
3. Ranks the players with short commentary on each (2-3 sentences per player)
4. **IMPORTANT: For each player, include their category scores on a line directly under their name**, formatted like: "Efficiency: 87.0 | Volume: 97.3 | Scoring: 85.1 | Receiving: 92.8"
5. Highlights what makes each player special
6. Mentions key stats that stand out
7. Ends with a brief conclusion about trends you notice

Format your response as JSON with these fields:
- title: The blog post title
- excerpt: A 1-2 sentence summary for previews
- content: The full markdown content
- tags: An array of 3-5 relevant tags

Example JSON format:
{{
  "title": "Your Title Here",
  "excerpt": "Brief summary here",
  "content": "# Full Markdown Content\\n\\nWith paragraphs...",
  "tags": ["power-rankings", "defense", "nfl"]
}}"""


PLAYER_SPOTLIGHT_PROMPT = """Write a Player Spotlight blog post about {player_name}.

Here is the player's data:
{player_data}

Additional context:
- Overall Rank: #{overall_rank} of {total_players}
- Position Rank: #{position_rank} among {position_total} {position}s
- Strengths: {strengths}
- Weaknesses: {weaknesses}

Create an in-depth blog post that:
1. Has an attention-grabbing title featuring the player
2. Opens with why this player is special
3. Breaks down their performance in each category (Run Defense, Pass Rush, Coverage, Playmaking)
4. Analyzes their raw stats and what they mean
5. Compares them to their position peers
6. Discusses their impact on their team
7. Concludes with your assessment of their season

Format your response as JSON with these fields:
- title: The blog post title
- excerpt: A 1-2 sentence summary for previews
- content: The full markdown content
- tags: An array of 3-5 relevant tags

Example JSON format:
{{
  "title": "Your Title Here",
  "excerpt": "Brief summary here",
  "content": "# Full Markdown Content\\n\\nWith paragraphs...",
  "tags": ["player-spotlight", "{position_lower}", "nfl"]
}}"""


POSITION_ANALYSIS_PROMPT = """Write a Position Analysis blog post for {position} players.

Here are the top {position} players:

{players_data}

Position Statistics:
- Total {position} players analyzed: {total_players}
- Average Overall Score: {avg_overall}
- Average Run Defense: {avg_run_defense}
- Average Pass Rush: {avg_pass_rush}
- Average Coverage: {avg_coverage}
- Average Playmaking: {avg_playmaking}

Create a comprehensive position breakdown that:
1. Has a title that captures the state of the position
2. Opens with the overall health/strength of this position group
3. Profiles the top 5 players with detailed analysis
4. Discusses what separates elite {position}s from the rest
5. Notes any interesting trends (specialists vs well-rounded, young vs veteran, etc.)
6. Concludes with predictions or observations about the position

Format your response as JSON with these fields:
- title: The blog post title
- excerpt: A 1-2 sentence summary for previews
- content: The full markdown content
- tags: An array of 3-5 relevant tags

Example JSON format:
{{
  "title": "Your Title Here",
  "excerpt": "Brief summary here",
  "content": "# Full Markdown Content\\n\\nWith paragraphs...",
  "tags": ["position-analysis", "{position_lower}", "nfl"]
}}"""


COMPARISON_PROMPT = """Write a Player Comparison blog post between {player1_name} and {player2_name}.

Player 1: {player1_name}
{player1_data}

Player 2: {player2_name}
{player2_data}

Head-to-Head Comparison:
{comparison_data}

Create an engaging comparison post that:
1. Has a title that captures the matchup (e.g., "Elite Edge Showdown: X vs Y")
2. Opens with why this comparison matters
3. Compares them category by category with analysis
4. Discusses their different styles/strengths
5. Looks at the raw stats behind the scores
6. Declares a winner (or explains why it's too close to call)
7. Concludes with what we can learn from comparing these players

Format your response as JSON with these fields:
- title: The blog post title
- excerpt: A 1-2 sentence summary for previews
- content: The full markdown content
- tags: An array of 3-5 relevant tags

Example JSON format:
{{
  "title": "Your Title Here",
  "excerpt": "Brief summary here",
  "content": "# Full Markdown Content\\n\\nWith paragraphs...",
  "tags": ["comparison", "defense", "nfl"]
}}"""


def format_player_data(player: dict, position_group: str = "DEF") -> str:
    """Format a single player's data for the prompt."""
    stats = player.get("stats", {})
    category_scores = player.get("category_scores", {})

    # Build category scores section
    categories = get_categories_for_group(position_group)
    category_lines = []
    for cat in categories:
        score = category_scores.get(cat["id"], player.get(f"{cat['id']}_score", 80.0))
        category_lines.append(f"- {cat['name']}: {score}")

    # Build raw stats section based on position group
    stat_lines = format_stats_for_group(stats, position_group)

    return f"""
Name: {player['name']}
Team: {player['team']}
Position: {player['position']}
Games Played: {player['games_played']}
Overall Score: {player['overall_score']}
{chr(10).join(category_lines)}

Raw Stats:
{chr(10).join(stat_lines)}
"""


def format_stats_for_group(stats: dict, position_group: str) -> list[str]:
    """Format raw stats based on position group."""
    if position_group == "DEF":
        return [
            f"- Tackles: {stats.get('tackles', 0)} (Solo: {stats.get('solo_tackles', 0)}, Assists: {stats.get('assists', 0)})",
            f"- Sacks: {stats.get('sacks', 0)}",
            f"- QB Hits: {stats.get('qb_hits', 0)}",
            f"- TFL: {stats.get('tackles_for_loss', 0)}",
            f"- Pass Deflections: {stats.get('passes_defended', 0)}",
            f"- Interceptions: {stats.get('interceptions', 0)}",
            f"- Forced Fumbles: {stats.get('forced_fumbles', 0)}",
            f"- Fumble Recoveries: {stats.get('fumble_recoveries', 0)}",
            f"- Defensive TDs: {stats.get('defensive_tds', 0)}",
        ]
    elif position_group == "RB":
        return [
            f"- Rush Attempts: {stats.get('rush_attempts', 0)}",
            f"- Rush Yards: {stats.get('rush_yards', 0)}",
            f"- Yards Per Carry: {stats.get('yards_per_carry', 0):.1f}",
            f"- Rush TDs: {stats.get('rush_tds', 0)}",
            f"- Receptions: {stats.get('receptions', 0)}",
            f"- Receiving Yards: {stats.get('rec_yards', 0)}",
            f"- Receiving TDs: {stats.get('rec_tds', 0)}",
            f"- Total Touches: {stats.get('touches', 0)}",
            f"- Total TDs: {stats.get('total_tds', 0)}",
        ]
    elif position_group == "QB":
        return [
            f"- Pass Attempts: {stats.get('pass_attempts', 0)}",
            f"- Completions: {stats.get('completions', 0)}",
            f"- Completion %: {stats.get('completion_pct', 0):.1f}%",
            f"- Pass Yards: {stats.get('pass_yards', 0)}",
            f"- Pass TDs: {stats.get('pass_tds', 0)}",
            f"- Interceptions: {stats.get('interceptions_thrown', 0)}",
            f"- Passer Rating: {stats.get('passer_rating', 0):.1f}",
            f"- Yards Per Attempt: {stats.get('yards_per_attempt', 0):.1f}",
        ]
    elif position_group in ("WR", "TE"):
        return [
            f"- Targets: {stats.get('targets', 0)}",
            f"- Receptions: {stats.get('receptions', 0)}",
            f"- Catch Rate: {stats.get('catch_rate', 0):.1f}%",
            f"- Receiving Yards: {stats.get('rec_yards', 0)}",
            f"- Yards Per Reception: {stats.get('yards_per_reception', 0):.1f}",
            f"- Receiving TDs: {stats.get('rec_tds', 0)}",
            f"- First Downs: {stats.get('first_downs', 0)}",
            f"- YAC: {stats.get('yards_after_catch', 0)}",
        ]
    elif position_group == "K":
        return [
            f"- FG Made: {stats.get('fg_made', 0)}",
            f"- FG Attempts: {stats.get('fg_attempts', 0)}",
            f"- FG %: {stats.get('fg_pct', 0):.1f}%",
            f"- XP Made: {stats.get('xp_made', 0)}",
            f"- XP %: {stats.get('xp_pct', 0):.1f}%",
            f"- Long FG: {stats.get('long_fg', 0)}",
            f"- Total Points: {stats.get('total_points', 0)}",
        ]
    else:
        # Generic fallback
        return [f"- {k}: {v}" for k, v in list(stats.items())[:10]]


def format_players_list(players: list[dict], position_group: str = "DEF") -> str:
    """Format a list of players for the prompt."""
    lines = []
    for i, player in enumerate(players, 1):
        lines.append(f"\n### #{i}. {player['name']} ({player['team']}, {player['position']})")
        lines.append(format_player_data(player, position_group))
    return "\n".join(lines)


def get_power_rankings_prompt(players: list[dict], position_group: str = "DEF") -> tuple[str, str]:
    """Get the system and user prompts for power rankings."""
    group_config = POSITION_GROUPS.get(position_group, POSITION_GROUPS["DEF"])
    group_name = group_config["name"].lower()

    user_prompt = POWER_RANKINGS_PROMPT.format(
        count=len(players),
        players_data=format_players_list(players, position_group),
    ).replace("defensive players", group_name).replace("defensive", group_name)

    return get_system_prompt(position_group), user_prompt


def get_spotlight_prompt(insight_data: dict) -> tuple[str, str]:
    """Get the system and user prompts for player spotlight."""
    player = insight_data["players"][0]
    stats = insight_data["stats"]

    user_prompt = PLAYER_SPOTLIGHT_PROMPT.format(
        player_name=player["name"],
        player_data=format_player_data(player),
        overall_rank=stats["overall_rank"],
        total_players=stats["total_players"],
        position_rank=stats["position_rank"],
        position_total=stats["position_total"],
        position=player["position"],
        strengths=", ".join(stats.get("strengths", [])),
        weaknesses=", ".join(stats.get("weaknesses", [])),
        position_lower=player["position"].lower(),
    )
    return SYSTEM_PROMPT, user_prompt


def get_position_analysis_prompt(insight_data: dict) -> tuple[str, str]:
    """Get the system and user prompts for position analysis."""
    players = insight_data["players"]
    stats = insight_data["stats"]
    position = insight_data["title"].split()[0]  # Extract position from title

    averages = stats.get("averages", {})

    user_prompt = POSITION_ANALYSIS_PROMPT.format(
        position=position,
        players_data=format_players_list(players[:10]),
        total_players=stats["total_players"],
        avg_overall=averages.get("overall_score", 80),
        avg_run_defense=averages.get("run_defense_score", 80),
        avg_pass_rush=averages.get("pass_rush_score", 80),
        avg_coverage=averages.get("coverage_score", 80),
        avg_playmaking=averages.get("playmaking_score", 80),
        position_lower=position.lower(),
    )
    return SYSTEM_PROMPT, user_prompt


def get_comparison_prompt(insight_data: dict) -> tuple[str, str]:
    """Get the system and user prompts for player comparison."""
    players = insight_data["players"]
    stats = insight_data["stats"]

    comparison_lines = []
    for category, data in stats.get("comparison", {}).items():
        p1_name = players[0]["name"]
        p2_name = players[1]["name"]
        comparison_lines.append(
            f"- {category}: {p1_name} ({data.get(p1_name, 'N/A')}) vs {p2_name} ({data.get(p2_name, 'N/A')}) - Advantage: {data.get('advantage', 'Tie')}"
        )

    user_prompt = COMPARISON_PROMPT.format(
        player1_name=players[0]["name"],
        player2_name=players[1]["name"],
        player1_data=format_player_data(players[0]),
        player2_data=format_player_data(players[1]),
        comparison_data="\n".join(comparison_lines),
    )
    return SYSTEM_PROMPT, user_prompt
