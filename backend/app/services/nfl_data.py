import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from app.core.ranking import calculate_category_scores, calculate_overall_score


# Position mapping for defensive players
DEFENSIVE_POSITIONS = {
    "DL": ["DT", "NT", "DE"],
    "EDGE": ["OLB", "DE", "EDGE"],
    "LB": ["ILB", "MLB", "LB"],
    "CB": ["CB"],
    "S": ["FS", "SS", "S", "DB"],
}

# Cache for fetched data
_data_cache: Optional[pd.DataFrame] = None


def map_position(position: str) -> str:
    """Map detailed positions to general defensive position groups."""
    if not position:
        return "DEF"
    position = str(position).upper()
    for group, positions in DEFENSIVE_POSITIONS.items():
        if position in positions:
            return group
    return position


def fetch_defensive_stats(season: int = 2023) -> pd.DataFrame:
    """
    Fetch defensive player statistics from play-by-play data.
    Returns a DataFrame with aggregated player stats.
    """
    global _data_cache

    if _data_cache is not None:
        return _data_cache

    try:
        import nfl_data_py as nfl

        print(f"Fetching {season} play-by-play data...")
        pbp = nfl.import_pbp_data([season])

        if pbp.empty:
            print("PBP data empty, using sample data")
            return _get_sample_data()

        # Get rosters for position info
        print("Fetching roster data...")
        rosters = nfl.import_seasonal_rosters([season])

        # Create player position lookup
        player_positions = {}
        player_teams = {}
        if not rosters.empty:
            for _, row in rosters.iterrows():
                pid = row.get('player_id')
                if pid:
                    player_positions[pid] = row.get('position', 'DEF')
                    player_teams[pid] = row.get('team', 'UNK')

        print("Aggregating defensive stats from play-by-play...")

        # Initialize stats dictionary
        player_stats = {}

        # Process tackles (solo and assist)
        for col_prefix, stat_name in [
            ('solo_tackle_1_player', 'solo_tackles'),
            ('solo_tackle_2_player', 'solo_tackles'),
            ('assist_tackle_1_player', 'assists'),
            ('assist_tackle_2_player', 'assists'),
            ('assist_tackle_3_player', 'assists'),
            ('assist_tackle_4_player', 'assists'),
        ]:
            id_col = f'{col_prefix}_id'
            name_col = f'{col_prefix}_name'
            if id_col in pbp.columns and name_col in pbp.columns:
                for _, row in pbp[[id_col, name_col]].dropna().iterrows():
                    pid = row[id_col]
                    pname = row[name_col]
                    if pid not in player_stats:
                        player_stats[pid] = {
                            'player_id': pid,
                            'player_name': pname,
                            'tackles': 0, 'solo_tackles': 0, 'assists': 0,
                            'sacks': 0, 'qb_hits': 0, 'tackles_for_loss': 0,
                            'passes_defended': 0, 'interceptions': 0,
                            'forced_fumbles': 0, 'fumble_recoveries': 0,
                            'defensive_tds': 0, 'games': set()
                        }
                    player_stats[pid][stat_name] += 1
                    player_stats[pid]['tackles'] += 1
                    if 'game_id' in row:
                        player_stats[pid]['games'].add(row['game_id'])

        # Process sacks
        if 'sack' in pbp.columns:
            sack_plays = pbp[pbp['sack'] == 1]
            for col in ['sack_player_id', 'half_sack_1_player_id', 'half_sack_2_player_id']:
                if col in sack_plays.columns:
                    name_col = col.replace('_id', '_name')
                    for _, row in sack_plays[[col, name_col, 'game_id']].dropna(subset=[col]).iterrows():
                        pid = row[col]
                        pname = row.get(name_col, 'Unknown')
                        if pid not in player_stats:
                            player_stats[pid] = {
                                'player_id': pid, 'player_name': pname,
                                'tackles': 0, 'solo_tackles': 0, 'assists': 0,
                                'sacks': 0, 'qb_hits': 0, 'tackles_for_loss': 0,
                                'passes_defended': 0, 'interceptions': 0,
                                'forced_fumbles': 0, 'fumble_recoveries': 0,
                                'defensive_tds': 0, 'games': set()
                            }
                        sack_val = 0.5 if 'half_sack' in col else 1.0
                        player_stats[pid]['sacks'] += sack_val
                        player_stats[pid]['games'].add(row['game_id'])

        # Process interceptions
        if 'interception_player_id' in pbp.columns:
            int_plays = pbp[pbp['interception'] == 1]
            for _, row in int_plays[['interception_player_id', 'interception_player_name', 'game_id']].dropna(subset=['interception_player_id']).iterrows():
                pid = row['interception_player_id']
                pname = row.get('interception_player_name', 'Unknown')
                if pid not in player_stats:
                    player_stats[pid] = {
                        'player_id': pid, 'player_name': pname,
                        'tackles': 0, 'solo_tackles': 0, 'assists': 0,
                        'sacks': 0, 'qb_hits': 0, 'tackles_for_loss': 0,
                        'passes_defended': 0, 'interceptions': 0,
                        'forced_fumbles': 0, 'fumble_recoveries': 0,
                        'defensive_tds': 0, 'games': set()
                    }
                player_stats[pid]['interceptions'] += 1
                player_stats[pid]['games'].add(row['game_id'])

        # Process forced fumbles
        if 'forced_fumble_player_1_player_id' in pbp.columns:
            ff_plays = pbp[pbp['fumble_forced'] == 1]
            for col in ['forced_fumble_player_1_player_id', 'forced_fumble_player_2_player_id']:
                if col in ff_plays.columns:
                    name_col = col.replace('_id', '_name')
                    for _, row in ff_plays[[col, name_col, 'game_id']].dropna(subset=[col]).iterrows():
                        pid = row[col]
                        pname = row.get(name_col, 'Unknown')
                        if pid not in player_stats:
                            player_stats[pid] = {
                                'player_id': pid, 'player_name': pname,
                                'tackles': 0, 'solo_tackles': 0, 'assists': 0,
                                'sacks': 0, 'qb_hits': 0, 'tackles_for_loss': 0,
                                'passes_defended': 0, 'interceptions': 0,
                                'forced_fumbles': 0, 'fumble_recoveries': 0,
                                'defensive_tds': 0, 'games': set()
                            }
                        player_stats[pid]['forced_fumbles'] += 1
                        player_stats[pid]['games'].add(row['game_id'])

        # Process fumble recoveries
        if 'fumble_recovery_1_player_id' in pbp.columns:
            fr_plays = pbp[pbp['fumble_lost'] == 1]
            for col in ['fumble_recovery_1_player_id', 'fumble_recovery_2_player_id']:
                if col in fr_plays.columns:
                    name_col = col.replace('_id', '_name')
                    for _, row in fr_plays[[col, name_col, 'game_id']].dropna(subset=[col]).iterrows():
                        pid = row[col]
                        pname = row.get(name_col, 'Unknown')
                        if pid not in player_stats:
                            player_stats[pid] = {
                                'player_id': pid, 'player_name': pname,
                                'tackles': 0, 'solo_tackles': 0, 'assists': 0,
                                'sacks': 0, 'qb_hits': 0, 'tackles_for_loss': 0,
                                'passes_defended': 0, 'interceptions': 0,
                                'forced_fumbles': 0, 'fumble_recoveries': 0,
                                'defensive_tds': 0, 'games': set()
                            }
                        player_stats[pid]['fumble_recoveries'] += 1
                        player_stats[pid]['games'].add(row['game_id'])

        # Process pass deflections
        if 'pass_defense_1_player_id' in pbp.columns:
            for col in ['pass_defense_1_player_id', 'pass_defense_2_player_id']:
                if col in pbp.columns:
                    name_col = col.replace('_id', '_name')
                    for _, row in pbp[[col, name_col, 'game_id']].dropna(subset=[col]).iterrows():
                        pid = row[col]
                        pname = row.get(name_col, 'Unknown')
                        if pid not in player_stats:
                            player_stats[pid] = {
                                'player_id': pid, 'player_name': pname,
                                'tackles': 0, 'solo_tackles': 0, 'assists': 0,
                                'sacks': 0, 'qb_hits': 0, 'tackles_for_loss': 0,
                                'passes_defended': 0, 'interceptions': 0,
                                'forced_fumbles': 0, 'fumble_recoveries': 0,
                                'defensive_tds': 0, 'games': set()
                            }
                        player_stats[pid]['passes_defended'] += 1
                        player_stats[pid]['games'].add(row['game_id'])

        # Process tackles for loss
        if 'tackled_for_loss' in pbp.columns:
            tfl_plays = pbp[pbp['tackled_for_loss'] == 1]
            for col in ['solo_tackle_1_player_id', 'solo_tackle_2_player_id',
                       'assist_tackle_1_player_id', 'assist_tackle_2_player_id']:
                if col in tfl_plays.columns:
                    for _, row in tfl_plays[[col, 'game_id']].dropna(subset=[col]).iterrows():
                        pid = row[col]
                        if pid in player_stats:
                            player_stats[pid]['tackles_for_loss'] += 1

        # Process QB hits
        if 'qb_hit_1_player_id' in pbp.columns:
            for col in ['qb_hit_1_player_id', 'qb_hit_2_player_id']:
                if col in pbp.columns:
                    name_col = col.replace('_id', '_name')
                    for _, row in pbp[[col, name_col, 'game_id']].dropna(subset=[col]).iterrows():
                        pid = row[col]
                        pname = row.get(name_col, 'Unknown')
                        if pid not in player_stats:
                            player_stats[pid] = {
                                'player_id': pid, 'player_name': pname,
                                'tackles': 0, 'solo_tackles': 0, 'assists': 0,
                                'sacks': 0, 'qb_hits': 0, 'tackles_for_loss': 0,
                                'passes_defended': 0, 'interceptions': 0,
                                'forced_fumbles': 0, 'fumble_recoveries': 0,
                                'defensive_tds': 0, 'games': set()
                            }
                        player_stats[pid]['qb_hits'] += 1
                        player_stats[pid]['games'].add(row['game_id'])

        # Convert to DataFrame
        stats_list = []
        for pid, stats in player_stats.items():
            stats['games_played'] = len(stats['games'])
            stats['position'] = player_positions.get(pid, 'DEF')
            stats['team'] = player_teams.get(pid, 'UNK')
            del stats['games']
            stats_list.append(stats)

        df = pd.DataFrame(stats_list)

        # Filter to only defensive positions with meaningful stats
        def_positions = ['CB', 'DB', 'DE', 'DT', 'FS', 'SS', 'ILB', 'OLB', 'LB', 'MLB', 'NT', 'S', 'EDGE']
        df = df[df['position'].isin(def_positions) | (df['tackles'] >= 10)]

        # Filter players with at least 1 game
        df = df[df['games_played'] >= 1]

        print(f"Found {len(df)} defensive players with stats")

        _data_cache = df
        return df

    except Exception as e:
        print(f"Error fetching NFL data: {e}")
        import traceback
        traceback.print_exc()
        return _get_sample_data()


def _get_sample_data() -> pd.DataFrame:
    """Return sample defensive data for development/testing."""
    sample_players = [
        {"player_id": "1", "player_name": "Micah Parsons", "position": "EDGE", "team": "DAL",
         "tackles": 64, "solo_tackles": 46, "assists": 18, "sacks": 14.0, "qb_hits": 20,
         "tackles_for_loss": 18, "passes_defended": 3, "interceptions": 0,
         "forced_fumbles": 3, "fumble_recoveries": 1, "defensive_tds": 0, "games_played": 17},
        {"player_id": "2", "player_name": "T.J. Watt", "position": "EDGE", "team": "PIT",
         "tackles": 68, "solo_tackles": 51, "assists": 17, "sacks": 19.0, "qb_hits": 25,
         "tackles_for_loss": 19, "passes_defended": 3, "interceptions": 1,
         "forced_fumbles": 4, "fumble_recoveries": 2, "defensive_tds": 0, "games_played": 15},
        {"player_id": "3", "player_name": "Myles Garrett", "position": "EDGE", "team": "CLE",
         "tackles": 42, "solo_tackles": 30, "assists": 12, "sacks": 14.0, "qb_hits": 18,
         "tackles_for_loss": 15, "passes_defended": 2, "interceptions": 0,
         "forced_fumbles": 4, "fumble_recoveries": 1, "defensive_tds": 1, "games_played": 14},
        {"player_id": "4", "player_name": "Fred Warner", "position": "LB", "team": "SF",
         "tackles": 132, "solo_tackles": 87, "assists": 45, "sacks": 4.0, "qb_hits": 6,
         "tackles_for_loss": 10, "passes_defended": 11, "interceptions": 2,
         "forced_fumbles": 1, "fumble_recoveries": 0, "defensive_tds": 0, "games_played": 17},
        {"player_id": "5", "player_name": "Roquan Smith", "position": "LB", "team": "BAL",
         "tackles": 169, "solo_tackles": 106, "assists": 63, "sacks": 3.5, "qb_hits": 7,
         "tackles_for_loss": 9, "passes_defended": 6, "interceptions": 2,
         "forced_fumbles": 2, "fumble_recoveries": 1, "defensive_tds": 0, "games_played": 17},
        {"player_id": "6", "player_name": "Sauce Gardner", "position": "CB", "team": "NYJ",
         "tackles": 58, "solo_tackles": 46, "assists": 12, "sacks": 0.0, "qb_hits": 0,
         "tackles_for_loss": 2, "passes_defended": 15, "interceptions": 4,
         "forced_fumbles": 1, "fumble_recoveries": 0, "defensive_tds": 0, "games_played": 17},
        {"player_id": "7", "player_name": "Jalen Ramsey", "position": "CB", "team": "MIA",
         "tackles": 46, "solo_tackles": 35, "assists": 11, "sacks": 1.0, "qb_hits": 2,
         "tackles_for_loss": 3, "passes_defended": 8, "interceptions": 1,
         "forced_fumbles": 1, "fumble_recoveries": 0, "defensive_tds": 0, "games_played": 11},
        {"player_id": "8", "player_name": "Derwin James", "position": "S", "team": "LAC",
         "tackles": 102, "solo_tackles": 68, "assists": 34, "sacks": 3.5, "qb_hits": 5,
         "tackles_for_loss": 8, "passes_defended": 7, "interceptions": 3,
         "forced_fumbles": 2, "fumble_recoveries": 1, "defensive_tds": 1, "games_played": 17},
        {"player_id": "9", "player_name": "Jessie Bates III", "position": "S", "team": "ATL",
         "tackles": 126, "solo_tackles": 92, "assists": 34, "sacks": 0.0, "qb_hits": 1,
         "tackles_for_loss": 3, "passes_defended": 8, "interceptions": 6,
         "forced_fumbles": 0, "fumble_recoveries": 1, "defensive_tds": 0, "games_played": 17},
        {"player_id": "10", "player_name": "Chris Jones", "position": "DL", "team": "KC",
         "tackles": 50, "solo_tackles": 35, "assists": 15, "sacks": 10.5, "qb_hits": 19,
         "tackles_for_loss": 14, "passes_defended": 3, "interceptions": 0,
         "forced_fumbles": 3, "fumble_recoveries": 0, "defensive_tds": 0, "games_played": 16},
        {"player_id": "11", "player_name": "Cameron Heyward", "position": "DL", "team": "PIT",
         "tackles": 67, "solo_tackles": 48, "assists": 19, "sacks": 4.0, "qb_hits": 12,
         "tackles_for_loss": 10, "passes_defended": 4, "interceptions": 0,
         "forced_fumbles": 1, "fumble_recoveries": 0, "defensive_tds": 0, "games_played": 11},
        {"player_id": "12", "player_name": "Quinnen Williams", "position": "DL", "team": "NYJ",
         "tackles": 55, "solo_tackles": 40, "assists": 15, "sacks": 5.0, "qb_hits": 11,
         "tackles_for_loss": 11, "passes_defended": 1, "interceptions": 0,
         "forced_fumbles": 1, "fumble_recoveries": 1, "defensive_tds": 0, "games_played": 13},
    ]
    return pd.DataFrame(sample_players)


def process_player_rankings(
    data: Optional[pd.DataFrame] = None,
    min_games: int = 1,
    position_filter: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
) -> List[Dict[str, Any]]:
    """
    Process player data and calculate rankings.

    Args:
        data: DataFrame with player stats (fetches if None)
        min_games: Minimum games played filter
        position_filter: Optional position group filter
        weights: Optional category weights

    Returns:
        List of player rankings sorted by overall score
    """
    if data is None:
        data = fetch_defensive_stats()  # Now uses real data!

    # Make a copy to avoid modifying original
    data = data.copy()

    # Filter by minimum games
    if "games_played" in data.columns:
        data = data[data["games_played"] >= min_games]

    # Filter by position
    if position_filter and position_filter != "All":
        if "position" in data.columns:
            data = data[data["position"].apply(map_position) == position_filter]

    if data.empty:
        return []

    # Convert stats to list of dicts for z-score calculation
    stat_cols = [
        "tackles", "solo_tackles", "assists", "sacks", "qb_hits",
        "tackles_for_loss", "passes_defended", "interceptions",
        "forced_fumbles", "fumble_recoveries", "defensive_tds"
    ]

    # Ensure all stat columns exist
    for col in stat_cols:
        if col not in data.columns:
            data[col] = 0.0

    all_stats = data[stat_cols].to_dict("records")

    # Calculate rankings for each player
    rankings = []
    for idx, row in data.iterrows():
        player_stats = {col: float(row.get(col, 0.0)) for col in stat_cols}
        category_scores = calculate_category_scores(player_stats, all_stats)
        overall = calculate_overall_score(category_scores, weights)

        player_id = row.get("player_id", str(idx))
        # Convert player_id to int if possible
        try:
            player_id_int = int(hash(player_id) % 1000000)
        except:
            player_id_int = idx + 1

        rankings.append({
            "id": player_id_int,
            "name": row.get("player_name", row.get("name", "Unknown")),
            "team": row.get("team", "UNK"),
            "position": map_position(row.get("position", "DEF")),
            "games_played": int(row.get("games_played", row.get("games", 0))),
            "overall_score": round(overall, 1),
            "run_defense_score": round(category_scores["run_defense"], 1),
            "pass_rush_score": round(category_scores["pass_rush"], 1),
            "coverage_score": round(category_scores["coverage"], 1),
            "playmaking_score": round(category_scores["playmaking"], 1),
            "stats": player_stats,
        })

    # Sort by overall score descending
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)

    return rankings
