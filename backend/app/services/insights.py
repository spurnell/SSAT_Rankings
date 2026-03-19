"""
Insights analyzer for NFL player rankings.
Detects interesting patterns and generates insights for blog posts.
"""
from typing import Any
from app.services.nfl_data_db import process_player_rankings, DEFENSIVE_POSITIONS
from app.core.position_config import POSITION_GROUPS, get_categories_for_group


def get_rankings_data(min_games: int = 8, position_group: str = "DEF") -> list[dict[str, Any]]:
    """Get rankings data with default minimum games filter."""
    return process_player_rankings(min_games=min_games, position_group=position_group)


def get_top_performers(rankings: list[dict], n: int = 10, position_group: str = "DEF") -> dict[str, Any]:
    """Get the top N overall performers."""
    top_players = rankings[:n]
    group_name = POSITION_GROUPS.get(position_group, {}).get("name", "Players")
    return {
        "insight_type": "top_performers",
        "title": f"Top {n} {group_name}",
        "description": f"The league's elite {group_name.lower()} based on overall score",
        "players": top_players,
        "position_group": position_group,
        "stats": {
            "avg_overall": round(sum(p["overall_score"] for p in top_players) / len(top_players), 1) if top_players else 0,
            "top_score": top_players[0]["overall_score"] if top_players else 0,
        },
    }


def get_position_leaders(rankings: list[dict]) -> dict[str, Any]:
    """Get the top player at each position group."""
    position_groups = ["EDGE", "LB", "DL", "CB", "S"]
    leaders = {}

    for position in position_groups:
        position_players = [p for p in rankings if p["position"] == position]
        if position_players:
            leaders[position] = position_players[0]

    return {
        "insight_type": "position_leaders",
        "title": "Position Group Leaders",
        "description": "Best player at each defensive position",
        "players": list(leaders.values()),
        "stats": {"positions_covered": list(leaders.keys())},
    }


def get_category_leaders(rankings: list[dict]) -> dict[str, Any]:
    """Get leaders in each scoring category."""
    categories = [
        ("run_defense_score", "Run Defense"),
        ("pass_rush_score", "Pass Rush"),
        ("coverage_score", "Coverage"),
        ("playmaking_score", "Playmaking"),
    ]

    leaders = {}
    for score_key, category_name in categories:
        sorted_by_category = sorted(rankings, key=lambda x: x[score_key], reverse=True)
        if sorted_by_category:
            leader = sorted_by_category[0]
            leaders[category_name] = {
                **leader,
                "category_score": leader[score_key],
            }

    return {
        "insight_type": "category_leaders",
        "title": "Category Leaders",
        "description": "Best performers in each scoring category",
        "players": list(leaders.values()),
        "stats": {"categories": [c[1] for c in categories]},
    }


def get_balanced_players(rankings: list[dict], threshold: float = 75.0) -> dict[str, Any]:
    """Find players who score well across all four categories."""
    categories = ["run_defense_score", "pass_rush_score", "coverage_score", "playmaking_score"]

    balanced = []
    for player in rankings:
        scores = [player[cat] for cat in categories]
        min_score = min(scores)
        if min_score >= threshold:
            balanced.append({
                **player,
                "min_category_score": min_score,
                "category_spread": max(scores) - min_score,
            })

    # Sort by minimum score (higher = more balanced at a high level)
    balanced.sort(key=lambda x: x["min_category_score"], reverse=True)

    return {
        "insight_type": "balanced_players",
        "title": "Most Complete Defenders",
        "description": f"Players scoring {threshold}+ in all four categories",
        "players": balanced[:10],
        "stats": {
            "count": len(balanced),
            "threshold": threshold,
        },
    }


def get_specialists(rankings: list[dict], elite_threshold: float = 90.0, avg_threshold: float = 75.0) -> dict[str, Any]:
    """Find specialists who dominate one category but are average in others."""
    categories = [
        ("run_defense_score", "Run Defense"),
        ("pass_rush_score", "Pass Rush"),
        ("coverage_score", "Coverage"),
        ("playmaking_score", "Playmaking"),
    ]

    specialists = []
    for player in rankings:
        scores = {cat_name: player[score_key] for score_key, cat_name in categories}

        for score_key, cat_name in categories:
            score = player[score_key]
            other_scores = [player[k] for k, n in categories if k != score_key]
            avg_other = sum(other_scores) / len(other_scores) if other_scores else 0

            if score >= elite_threshold and avg_other < avg_threshold:
                specialists.append({
                    **player,
                    "specialty": cat_name,
                    "specialty_score": score,
                    "avg_other_categories": round(avg_other, 1),
                })
                break

    specialists.sort(key=lambda x: x["specialty_score"], reverse=True)

    return {
        "insight_type": "specialists",
        "title": "Elite Specialists",
        "description": f"Players dominating one category ({elite_threshold}+) while average in others",
        "players": specialists[:10],
        "stats": {
            "count": len(specialists),
            "elite_threshold": elite_threshold,
        },
    }


def get_position_breakdown(rankings: list[dict], position: str, position_group: str = "DEF") -> dict[str, Any]:
    """Get detailed breakdown for a specific position or position group."""
    # For non-DEF groups, use all players (they're already filtered by position group)
    if position_group != "DEF":
        position_players = rankings
    else:
        position_players = [p for p in rankings if p["position"] == position]

    if not position_players:
        return {
            "insight_type": "position_breakdown",
            "title": f"{position} Position Analysis",
            "description": f"No players found for position {position}",
            "players": [],
            "stats": {},
            "position_group": position_group,
        }

    # Get categories for this position group
    categories_config = get_categories_for_group(position_group)
    category_keys = ["overall_score"] + [f"{cat['id']}_score" for cat in categories_config]

    # Calculate position averages
    averages = {}
    for cat_key in category_keys:
        if cat_key == "overall_score":
            values = [p.get("overall_score", 80) for p in position_players]
        else:
            cat_id = cat_key.replace("_score", "")
            values = [p.get("category_scores", {}).get(cat_id, 80) for p in position_players]
        averages[cat_key] = round(sum(values) / len(values), 1) if values else 80.0

    return {
        "insight_type": "position_breakdown",
        "title": f"{position} Position Analysis",
        "description": f"Breakdown of top {position} players",
        "players": position_players[:15],
        "position_group": position_group,
        "stats": {
            "total_players": len(position_players),
            "averages": averages,
            "top_player": position_players[0]["name"] if position_players else None,
        },
    }


def get_player_comparison(rankings: list[dict], player1_name: str, player2_name: str) -> dict[str, Any]:
    """Compare two players head-to-head."""

    def find_player(name: str) -> dict | None:
        for p in rankings:
            if name.lower() in p["name"].lower():
                return p
        return None

    p1 = find_player(player1_name)
    p2 = find_player(player2_name)

    if not p1 or not p2:
        missing = []
        if not p1:
            missing.append(player1_name)
        if not p2:
            missing.append(player2_name)
        return {
            "insight_type": "comparison",
            "title": "Player Comparison",
            "description": f"Could not find player(s): {', '.join(missing)}",
            "players": [],
            "stats": {"error": "Player not found"},
        }

    categories = [
        ("overall_score", "Overall"),
        ("run_defense_score", "Run Defense"),
        ("pass_rush_score", "Pass Rush"),
        ("coverage_score", "Coverage"),
        ("playmaking_score", "Playmaking"),
    ]

    comparison = {}
    for score_key, cat_name in categories:
        comparison[cat_name] = {
            p1["name"]: p1[score_key],
            p2["name"]: p2[score_key],
            "advantage": p1["name"] if p1[score_key] > p2[score_key] else p2["name"],
        }

    return {
        "insight_type": "comparison",
        "title": f"{p1['name']} vs {p2['name']}",
        "description": f"Head-to-head comparison of {p1['name']} ({p1['team']}) and {p2['name']} ({p2['team']})",
        "players": [p1, p2],
        "stats": {"comparison": comparison},
    }


def get_player_spotlight(rankings: list[dict], player_name: str) -> dict[str, Any]:
    """Get detailed spotlight data for a specific player."""

    def find_player(name: str) -> dict | None:
        for p in rankings:
            if name.lower() in p["name"].lower():
                return p
        return None

    player = find_player(player_name)

    if not player:
        return {
            "insight_type": "spotlight",
            "title": "Player Spotlight",
            "description": f"Could not find player: {player_name}",
            "players": [],
            "stats": {"error": "Player not found"},
        }

    # Find player's rank overall and by position
    overall_rank = rankings.index(player) + 1
    position_players = [p for p in rankings if p["position"] == player["position"]]
    position_rank = position_players.index(player) + 1 if player in position_players else 0

    # Find strengths and weaknesses
    categories = [
        ("run_defense_score", "Run Defense"),
        ("pass_rush_score", "Pass Rush"),
        ("coverage_score", "Coverage"),
        ("playmaking_score", "Playmaking"),
    ]

    scores_with_names = [(player[k], name) for k, name in categories]
    scores_with_names.sort(reverse=True)
    strengths = [name for score, name in scores_with_names[:2]]
    weaknesses = [name for score, name in scores_with_names[-1:]]

    return {
        "insight_type": "spotlight",
        "title": f"Player Spotlight: {player['name']}",
        "description": f"Deep dive on {player['name']} ({player['team']}, {player['position']})",
        "players": [player],
        "stats": {
            "overall_rank": overall_rank,
            "position_rank": position_rank,
            "total_players": len(rankings),
            "position_total": len(position_players),
            "strengths": strengths,
            "weaknesses": weaknesses,
        },
    }


def get_all_insights(min_games: int = 8) -> dict[str, Any]:
    """Get a summary of all available insights."""
    rankings = get_rankings_data(min_games)

    if not rankings:
        return {"error": "No rankings data available", "insights": []}

    return {
        "total_players": len(rankings),
        "min_games_filter": min_games,
        "insights": [
            get_top_performers(rankings),
            get_position_leaders(rankings),
            get_category_leaders(rankings),
            get_balanced_players(rankings),
            get_specialists(rankings),
        ],
        "available_positions": list(DEFENSIVE_POSITIONS.keys()),
    }
