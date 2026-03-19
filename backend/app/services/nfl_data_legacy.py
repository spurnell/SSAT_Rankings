import pandas as pd
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
import json

from app.core.config import settings
from app.core.ranking import (
    calculate_raw_category_z_scores,
    normalize_scores_to_range,
)
from app.core.position_config import (
    get_position_group,
    get_categories_for_group,
    get_category_weights,
    get_log_scale_stats,
    POSITION_GROUPS,
)


# Position mapping for defensive players
DEFENSIVE_POSITIONS = {
    "DL": ["DT", "NT", "DE"],
    "EDGE": ["OLB", "DE", "EDGE"],
    "LB": ["ILB", "MLB", "LB"],
    "CB": ["CB"],
    "S": ["FS", "SS", "S", "DB"],
}

# Cache for fetched data by data source
_data_cache: Dict[str, pd.DataFrame] = {}

# File-based cache directory
_CACHE_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "cache"


def _save_to_file_cache(cache_key: str, df: pd.DataFrame) -> None:
    """Save a DataFrame to the file cache as CSV."""
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = _CACHE_DIR / f"{cache_key}.csv"
        df.to_csv(cache_path, index=False)
        print(f"Saved {len(df)} rows to file cache: {cache_path}")
    except Exception as e:
        print(f"Warning: Could not save to file cache: {e}")


def _load_from_file_cache(cache_key: str) -> Optional[pd.DataFrame]:
    """Load a DataFrame from the file cache if it exists."""
    cache_path = _CACHE_DIR / f"{cache_key}.csv"
    if cache_path.exists():
        try:
            df = pd.read_csv(cache_path)
            print(f"Loaded {len(df)} rows from file cache: {cache_path}")
            return df
        except Exception as e:
            print(f"Warning: Could not load from file cache: {e}")
    return None


def find_column(df: pd.DataFrame, candidates: List[str], exact_first: bool = True) -> Optional[str]:
    """
    Find a column in DataFrame by searching through candidate names.

    Args:
        df: DataFrame to search
        candidates: List of possible column name substrings to look for
        exact_first: If True, try exact matches before substring matches

    Returns:
        Column name if found, None otherwise
    """
    # Try exact matches first
    if exact_first:
        for candidate in candidates:
            if candidate in df.columns:
                return candidate

    # Then try case-insensitive substring matches
    for col in df.columns:
        col_lower = col.lower()
        for candidate in candidates:
            if candidate.lower() == col_lower:
                return col

    # Finally try partial matches (column contains candidate)
    for col in df.columns:
        col_lower = col.lower()
        for candidate in candidates:
            if candidate.lower() in col_lower:
                return col

    return None


def clear_cache(include_file_cache: bool = False):
    """Clear the data cache. Optionally also clear the file-based cache."""
    global _data_cache
    _data_cache = {}
    if include_file_cache and _CACHE_DIR.exists():
        for f in _CACHE_DIR.glob("*.csv"):
            f.unlink()
        print("File cache cleared")


def map_position(position: str) -> str:
    """Map detailed positions to general defensive position groups."""
    if not position:
        return "DEF"
    position = str(position).upper()
    for group, positions in DEFENSIVE_POSITIONS.items():
        if position in positions:
            return group
    return position


def fetch_defensive_stats(season: int = settings.current_season) -> pd.DataFrame:
    """
    Fetch defensive player statistics from Pro Football Reference.
    Returns a DataFrame with season stats for all defensive players.
    """
    global _data_cache

    cache_key = f"defense_{season}"
    if cache_key in _data_cache:
        return _data_cache[cache_key]

    # Try file cache before fetching from network
    file_cached = _load_from_file_cache(cache_key)
    if file_cached is not None:
        _data_cache[cache_key] = file_cached
        return file_cached

    try:
        print(f"Fetching {season} defensive stats from Pro Football Reference...")
        url = f'https://www.pro-football-reference.com/years/{season}/defense.htm'
        tables = pd.read_html(url)

        if not tables:
            print("No tables found, using sample data")
            return _get_sample_defensive_data()

        df = tables[0]

        # Flatten multi-level column names
        df.columns = [col[1] if col[0].startswith('Unnamed') else f'{col[0]}_{col[1]}' for col in df.columns]

        # Remove header rows that appear in the middle of data
        df = df[df['Rk'] != 'Rk'].copy()

        # Map PFR columns to our expected column names
        column_map = {
            'Player': 'player_name',
            'Team': 'team',
            'Pos': 'position',
            'G': 'games_played',
            'Tackles_Comb': 'tackles',
            'Tackles_Solo': 'solo_tackles',
            'Tackles_Ast': 'assists',
            'Sk': 'sacks',
            'Tackles_QBHits': 'qb_hits',
            'Tackles_TFL': 'tackles_for_loss',
            'Def Interceptions_PD': 'passes_defended',
            'Def Interceptions_Int': 'interceptions',
            'Fumbles_FF': 'forced_fumbles',
            'Fumbles_FR': 'fumble_recoveries',
            'Def Interceptions_IntTD': 'defensive_tds',
        }

        # Rename columns
        df = df.rename(columns=column_map)

        # Keep only the columns we need
        keep_cols = list(column_map.values())
        df = df[[c for c in keep_cols if c in df.columns]]

        # Convert numeric columns
        numeric_cols = ['games_played', 'tackles', 'solo_tackles', 'assists', 'sacks',
                       'qb_hits', 'tackles_for_loss', 'passes_defended', 'interceptions',
                       'forced_fumbles', 'fumble_recoveries', 'defensive_tds']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Clean player names (remove asterisks/special chars)
        df['player_name'] = df['player_name'].str.replace(r'[*+]', '', regex=True).str.strip()

        # Add player_id based on index
        df['player_id'] = range(1, len(df) + 1)

        # Normalize position names (PFR uses RDE, LCB, etc.)
        def normalize_position(pos):
            if pd.isna(pos):
                return 'DEF'
            pos = str(pos).upper()
            # Strip L/R prefix only if result is a valid position
            if pos.startswith(('L', 'R')) and len(pos) > 2:
                pos = pos[1:]
            return pos

        df['position'] = df['position'].apply(normalize_position)

        # Filter to defensive positions
        def_positions = ['CB', 'DB', 'DE', 'DT', 'FS', 'SS', 'ILB', 'OLB', 'LB', 'MLB', 'NT', 'S', 'EDGE']
        df = df[df['position'].isin(def_positions)]

        # Filter players with at least 1 game
        df = df[df['games_played'] >= 1]

        print(f"Found {len(df)} defensive players with stats")

        _data_cache[cache_key] = df
        _save_to_file_cache(cache_key, df)
        return df

    except Exception as e:
        print(f"Error fetching defensive data: {e}")
        import traceback
        traceback.print_exc()
        file_cached = _load_from_file_cache(cache_key)
        if file_cached is not None:
            _data_cache[cache_key] = file_cached
            return file_cached
        return _get_sample_defensive_data()


def fetch_passing_stats(season: int = settings.current_season) -> pd.DataFrame:
    """Fetch QB passing stats from Pro Football Reference."""
    global _data_cache

    cache_key = f"passing_{season}"
    if cache_key in _data_cache:
        return _data_cache[cache_key]

    # Try file cache before fetching from network
    file_cached = _load_from_file_cache(cache_key)
    if file_cached is not None:
        _data_cache[cache_key] = file_cached
        return file_cached

    try:
        print(f"Fetching {season} passing stats from Pro Football Reference...")
        url = f'https://www.pro-football-reference.com/years/{season}/passing.htm'
        tables = pd.read_html(url)

        if not tables:
            print("No tables found, using sample data")
            return _get_sample_passing_data()

        df = tables[0]

        # Handle multi-level columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[1] if col[0].startswith('Unnamed') else f'{col[0]}_{col[1]}' for col in df.columns]

        # Remove header rows
        if 'Rk' in df.columns:
            df = df[df['Rk'] != 'Rk'].copy()


        # Map columns using flexible column search
        # Player name
        player_col = find_column(df, ['Player'])
        if player_col:
            df['player_name'] = df[player_col].astype(str).str.replace(r'[*+]', '', regex=True).str.strip()

        # Team - try both 'Tm' and 'Team'
        team_col = find_column(df, ['Tm', 'Team'])
        if team_col:
            df['team'] = df[team_col]
        else:
            df['team'] = 'UNK'

        # Position
        pos_col = find_column(df, ['Pos', 'Position'])
        if pos_col:
            df['position'] = df[pos_col]

        # Games played
        games_col = find_column(df, ['G', 'Games'])
        if games_col:
            df['games_played'] = pd.to_numeric(df[games_col], errors='coerce').fillna(0)

        # Map remaining columns
        column_map = {
            'Att': 'pass_attempts',
            'Cmp': 'completions',
            'Cmp%': 'completion_pct',
            'Yds': 'pass_yards',
            'TD': 'pass_tds',
            'Int': 'interceptions',
            'Rate': 'passer_rating',
            'Y/A': 'yards_per_attempt',
            'Sk': 'sacks',
            'Yds.1': 'sack_yards',
            '1D': 'first_downs',
        }

        for old_col, new_col in column_map.items():
            if old_col in df.columns:
                df = df.rename(columns={old_col: new_col})

        # Convert numeric columns
        numeric_cols = ['games_played', 'pass_attempts', 'completions', 'completion_pct',
                       'pass_yards', 'pass_tds', 'interceptions', 'passer_rating',
                       'yards_per_attempt', 'sacks', 'sack_yards', 'first_downs']
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Add calculated stats for ball security (inverted - higher is better)
        if 'interceptions' in df.columns and 'pass_attempts' in df.columns:
            df['int_rate_inv'] = df.apply(
                lambda x: 100 - (x['interceptions'] / max(x['pass_attempts'], 1)) * 100,
                axis=1
            )
        if 'sacks' in df.columns and 'pass_attempts' in df.columns:
            df['sack_rate_inv'] = df.apply(
                lambda x: 100 - (x['sacks'] / max(x['pass_attempts'], 1)) * 100,
                axis=1
            )

        # Add fumbles_inv (placeholder - PFR may not have this directly)
        df['fumbles'] = 0
        df['fumbles_inv'] = 100  # No fumbles = perfect score

        # Add player_id
        df['player_id'] = range(1, len(df) + 1)

        # Filter to QBs only
        if 'position' in df.columns:
            df = df[df['position'].str.upper() == 'QB']

        # Filter by minimum attempts (to exclude backup QBs with few plays)
        if 'pass_attempts' in df.columns:
            df = df[df['pass_attempts'] >= 50]

        print(f"Found {len(df)} QBs with stats")

        _data_cache[cache_key] = df
        _save_to_file_cache(cache_key, df)
        return df

    except Exception as e:
        print(f"Error fetching passing data: {e}")
        import traceback
        traceback.print_exc()
        file_cached = _load_from_file_cache(cache_key)
        if file_cached is not None:
            _data_cache[cache_key] = file_cached
            return file_cached
        return _get_sample_passing_data()


def _merge_rb_receiving_stats(rushing_df: pd.DataFrame, season: int) -> pd.DataFrame:
    """
    Merge receiving stats into rushing DataFrame for RBs.
    Fetches receiving data and joins on player name + team.
    """
    try:
        print("Fetching receiving stats for RBs...")
        url = f'https://www.pro-football-reference.com/years/{season}/receiving.htm'
        tables = pd.read_html(url)

        if not tables:
            print("No receiving tables found, using zero receiving stats")
            rushing_df['receptions'] = 0
            rushing_df['rec_yards'] = 0
            rushing_df['rec_tds'] = 0
            rushing_df['targets'] = 0
            return rushing_df

        rec_df = tables[0]

        # Handle multi-level columns
        if isinstance(rec_df.columns, pd.MultiIndex):
            rec_df.columns = [col[1] if col[0].startswith('Unnamed') else f'{col[0]}_{col[1]}' for col in rec_df.columns]

        # Remove header rows
        if 'Rk' in rec_df.columns:
            rec_df = rec_df[rec_df['Rk'] != 'Rk'].copy()

        # Extract player name
        player_col = find_column(rec_df, ['Player'])
        if player_col:
            rec_df['player_name'] = rec_df[player_col].astype(str).str.replace(r'[*+]', '', regex=True).str.strip()

        # Extract team
        team_col = find_column(rec_df, ['Tm', 'Team'])
        if team_col:
            rec_df['team'] = rec_df[team_col]

        # Extract receiving stats
        tgt_col = find_column(rec_df, ['Receiving_Tgt', 'Tgt'])
        rec_df['targets'] = pd.to_numeric(rec_df[tgt_col], errors='coerce').fillna(0) if tgt_col else 0

        rec_col = find_column(rec_df, ['Receiving_Rec', 'Rec'])
        rec_df['receptions'] = pd.to_numeric(rec_df[rec_col], errors='coerce').fillna(0) if rec_col else 0

        yds_col = find_column(rec_df, ['Receiving_Yds', 'Yds'])
        rec_df['rec_yards'] = pd.to_numeric(rec_df[yds_col], errors='coerce').fillna(0) if yds_col else 0

        td_col = find_column(rec_df, ['Receiving_TD', 'TD'])
        rec_df['rec_tds'] = pd.to_numeric(rec_df[td_col], errors='coerce').fillna(0) if td_col else 0

        # Filter receiving data to only RBs/FBs
        pos_col = find_column(rec_df, ['Pos', 'Position'])
        if pos_col:
            rec_df['position'] = rec_df[pos_col]
            pos_upper = rec_df['position'].str.upper()
            rb_rec_mask = pos_upper.isin(['RB', 'FB', 'HB'])
            rec_df = rec_df[rb_rec_mask]

        # Keep only columns we need for merge
        rec_df = rec_df[['player_name', 'team', 'targets', 'receptions', 'rec_yards', 'rec_tds']].copy()

        # Merge on player_name and team
        rushing_df = rushing_df.merge(
            rec_df,
            on=['player_name', 'team'],
            how='left',
            suffixes=('', '_rec')
        )

        # Fill NaN receiving stats with 0
        for col in ['targets', 'receptions', 'rec_yards', 'rec_tds']:
            if col not in rushing_df.columns:
                rushing_df[col] = 0
            else:
                rushing_df[col] = rushing_df[col].fillna(0)

        print(f"Merged receiving stats for {(rushing_df['receptions'] > 0).sum()} RBs")
        return rushing_df

    except Exception as e:
        print(f"Error fetching receiving stats for RBs: {e}")
        import traceback
        traceback.print_exc()
        # Fall back to zero receiving stats
        rushing_df['receptions'] = 0
        rushing_df['rec_yards'] = 0
        rushing_df['rec_tds'] = 0
        rushing_df['targets'] = 0
        return rushing_df


def fetch_rushing_stats(season: int = settings.current_season) -> pd.DataFrame:
    """Fetch RB rushing stats from Pro Football Reference."""
    global _data_cache

    cache_key = f"rushing_{season}"
    if cache_key in _data_cache:
        return _data_cache[cache_key]

    # Try file cache before fetching from network
    file_cached = _load_from_file_cache(cache_key)
    if file_cached is not None:
        _data_cache[cache_key] = file_cached
        return file_cached

    try:
        print(f"Fetching {season} rushing stats from Pro Football Reference...")
        url = f'https://www.pro-football-reference.com/years/{season}/rushing.htm'
        tables = pd.read_html(url)

        if not tables:
            print("No tables found, using sample data")
            return _get_sample_rushing_data()

        df = tables[0]

        # Handle multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[1] if col[0].startswith('Unnamed') else f'{col[0]}_{col[1]}' for col in df.columns]

        # Remove header rows
        if 'Rk' in df.columns:
            df = df[df['Rk'] != 'Rk'].copy()


        # Map columns using flexible column search
        # Player name
        player_col = find_column(df, ['Player'])
        if player_col:
            df['player_name'] = df[player_col].astype(str).str.replace(r'[*+]', '', regex=True).str.strip()

        # Team - try both 'Tm' and 'Team'
        team_col = find_column(df, ['Tm', 'Team'])
        if team_col:
            df['team'] = df[team_col]
        else:
            df['team'] = 'UNK'

        # Position
        pos_col = find_column(df, ['Pos', 'Position'])
        if pos_col:
            df['position'] = df[pos_col]
        else:
            # If no position column, default to RB since this is the rushing table
            df['position'] = 'RB'

        # Games played
        games_col = find_column(df, ['G', 'Games'])
        if games_col:
            df['games_played'] = pd.to_numeric(df[games_col], errors='coerce').fillna(0)

        # Map remaining columns - check for Rushing_ prefix and bare column names
        # Rush attempts
        att_col = find_column(df, ['Rushing_Att', 'Att'])
        if att_col:
            df['rush_attempts'] = pd.to_numeric(df[att_col], errors='coerce').fillna(0)
        else:
            df['rush_attempts'] = 0

        # Rush yards
        yds_col = find_column(df, ['Rushing_Yds', 'Yds'])
        if yds_col:
            df['rush_yards'] = pd.to_numeric(df[yds_col], errors='coerce').fillna(0)
        else:
            df['rush_yards'] = 0

        # Yards per carry
        ypa_col = find_column(df, ['Rushing_Y/A', 'Y/A'])
        if ypa_col:
            df['yards_per_carry'] = pd.to_numeric(df[ypa_col], errors='coerce').fillna(0)
        else:
            df['yards_per_carry'] = 0

        # Rush TDs
        td_col = find_column(df, ['Rushing_TD', 'TD'])
        if td_col:
            df['rush_tds'] = pd.to_numeric(df[td_col], errors='coerce').fillna(0)
        else:
            df['rush_tds'] = 0

        # First downs
        fd_col = find_column(df, ['Rushing_1D', '1D'])
        if fd_col:
            df['first_downs'] = pd.to_numeric(df[fd_col], errors='coerce').fillna(0)
        else:
            df['first_downs'] = 0

        # Longest rush
        lng_col = find_column(df, ['Rushing_Lng', 'Lng'])
        if lng_col:
            df['longest_rush'] = pd.to_numeric(df[lng_col], errors='coerce').fillna(0)
        else:
            df['longest_rush'] = 0

        # Fumbles
        fmb_col = find_column(df, ['Fmb', 'Fumbles'])
        if fmb_col:
            df['fumbles'] = pd.to_numeric(df[fmb_col], errors='coerce').fillna(0)
        else:
            df['fumbles'] = 0

        # Add player_id
        df['player_id'] = range(1, len(df) + 1)

        # Filter to RBs/FBs only - but be flexible if position column doesn't have expected values
        if 'position' in df.columns:
            # Check if we have any RB/FB in the position column
            pos_upper = df['position'].str.upper()
            rb_mask = pos_upper.isin(['RB', 'FB', 'HB'])
            if rb_mask.sum() > 0:
                df = df[rb_mask]
            # else: keep all players since position column may not be reliable

        # Filter by minimum attempts
        if 'rush_attempts' in df.columns:
            df = df[df['rush_attempts'] >= 20]

        # Merge receiving stats from receiving table
        df = _merge_rb_receiving_stats(df, season)

        # Calculate derived stats (after merge so receiving stats are populated)
        df['touches'] = df['rush_attempts'] + df['receptions']
        df['yards_per_touch'] = df.apply(
            lambda x: (x['rush_yards'] + x['rec_yards']) / max(x['touches'], 1),
            axis=1
        )
        df['total_tds'] = df['rush_tds'] + df['rec_tds']
        df['success_rate'] = 50.0  # Placeholder - would need play-by-play data

        print(f"Found {len(df)} RBs with stats")

        _data_cache[cache_key] = df
        _save_to_file_cache(cache_key, df)
        return df

    except Exception as e:
        print(f"Error fetching rushing data: {e}")
        import traceback
        traceback.print_exc()
        file_cached = _load_from_file_cache(cache_key)
        if file_cached is not None:
            _data_cache[cache_key] = file_cached
            return file_cached
        return _get_sample_rushing_data()


def fetch_receiving_stats(season: int = settings.current_season, position_filter: Optional[str] = None) -> pd.DataFrame:
    """Fetch WR/TE receiving stats from Pro Football Reference."""
    global _data_cache

    cache_key = f"receiving_{season}"
    if cache_key in _data_cache:
        df = _data_cache[cache_key].copy()
        if position_filter:
            filtered = df[df['position'].str.upper() == position_filter.upper()]
            if len(filtered) > 0:
                return filtered
            print(f"Warning: No players found for position {position_filter} in cache, returning all receivers")
        return df

    # Try file cache before fetching from network
    file_cached = _load_from_file_cache(cache_key)
    if file_cached is not None:
        _data_cache[cache_key] = file_cached
        df = file_cached.copy()
        if position_filter:
            filtered = df[df['position'].str.upper() == position_filter.upper()]
            if len(filtered) > 0:
                return filtered
        return df

    try:
        print(f"Fetching {season} receiving stats from Pro Football Reference...")
        url = f'https://www.pro-football-reference.com/years/{season}/receiving.htm'
        tables = pd.read_html(url)

        if not tables:
            print("No tables found, using sample data")
            return _get_sample_receiving_data(position_filter)

        df = tables[0]

        # Handle multi-level columns
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[1] if col[0].startswith('Unnamed') else f'{col[0]}_{col[1]}' for col in df.columns]

        # Remove header rows
        if 'Rk' in df.columns:
            df = df[df['Rk'] != 'Rk'].copy()


        # Map columns using flexible column search
        # Player name
        player_col = find_column(df, ['Player'])
        if player_col:
            df['player_name'] = df[player_col].astype(str).str.replace(r'[*+]', '', regex=True).str.strip()

        # Team - try both 'Tm' and 'Team'
        team_col = find_column(df, ['Tm', 'Team'])
        if team_col:
            df['team'] = df[team_col]
        else:
            df['team'] = 'UNK'

        # Position
        pos_col = find_column(df, ['Pos', 'Position'])
        if pos_col:
            df['position'] = df[pos_col]
        else:
            # If no position column, we'll handle this later
            df['position'] = 'WR'

        # Games played
        games_col = find_column(df, ['G', 'Games'])
        if games_col:
            df['games_played'] = pd.to_numeric(df[games_col], errors='coerce').fillna(0)

        # Map remaining columns - check for Receiving_ prefix and bare column names
        # Targets
        tgt_col = find_column(df, ['Receiving_Tgt', 'Tgt'])
        if tgt_col:
            df['targets'] = pd.to_numeric(df[tgt_col], errors='coerce').fillna(0)
        else:
            df['targets'] = 0

        # Receptions
        rec_col = find_column(df, ['Receiving_Rec', 'Rec'])
        if rec_col:
            df['receptions'] = pd.to_numeric(df[rec_col], errors='coerce').fillna(0)
        else:
            df['receptions'] = 0

        # Receiving yards
        yds_col = find_column(df, ['Receiving_Yds', 'Yds'])
        if yds_col:
            df['rec_yards'] = pd.to_numeric(df[yds_col], errors='coerce').fillna(0)
        else:
            df['rec_yards'] = 0

        # Yards per reception
        ypr_col = find_column(df, ['Receiving_Y/R', 'Y/R'])
        if ypr_col:
            df['yards_per_reception'] = pd.to_numeric(df[ypr_col], errors='coerce').fillna(0)
        else:
            df['yards_per_reception'] = 0

        # Yards per target
        ypt_col = find_column(df, ['Receiving_Y/Tgt', 'Y/Tgt'])
        if ypt_col:
            df['yards_per_target'] = pd.to_numeric(df[ypt_col], errors='coerce').fillna(0)
        else:
            df['yards_per_target'] = 0

        # Receiving TDs
        td_col = find_column(df, ['Receiving_TD', 'TD'])
        if td_col:
            df['rec_tds'] = pd.to_numeric(df[td_col], errors='coerce').fillna(0)
        else:
            df['rec_tds'] = 0

        # First downs
        fd_col = find_column(df, ['Receiving_1D', '1D'])
        if fd_col:
            df['first_downs'] = pd.to_numeric(df[fd_col], errors='coerce').fillna(0)
        else:
            df['first_downs'] = 0

        # Catch rate
        catch_col = find_column(df, ['Receiving_Ctch%', 'Ctch%'])
        if catch_col:
            df['catch_rate'] = df[catch_col].astype(str).str.replace('%', '')
            df['catch_rate'] = pd.to_numeric(df['catch_rate'], errors='coerce').fillna(0)
        else:
            df['catch_rate'] = 0

        # Longest reception
        lng_col = find_column(df, ['Receiving_Lng', 'Lng'])
        if lng_col:
            df['longest_rec'] = pd.to_numeric(df[lng_col], errors='coerce').fillna(0)
        else:
            df['longest_rec'] = 0

        # Fumbles
        fmb_col = find_column(df, ['Fmb', 'Fumbles'])
        if fmb_col:
            df['fumbles'] = pd.to_numeric(df[fmb_col], errors='coerce').fillna(0)
        else:
            df['fumbles'] = 0

        # Add player_id
        df['player_id'] = range(1, len(df) + 1)

        # Calculate YAC if not available (placeholder)
        if 'yards_after_catch' not in df.columns:
            df['yards_after_catch'] = df['rec_yards'] * 0.4  # Rough estimate

        # Calculate catch rate if not available
        if 'catch_rate' not in df.columns or df['catch_rate'].sum() == 0:
            df['catch_rate'] = df.apply(
                lambda x: (x['receptions'] / max(x['targets'], 1)) * 100,
                axis=1
            )

        # Calculate yards per target if not available
        if 'yards_per_target' not in df.columns or df['yards_per_target'].sum() == 0:
            df['yards_per_target'] = df.apply(
                lambda x: x['rec_yards'] / max(x['targets'], 1),
                axis=1
            )

        # Filter to valid receiver positions (WR, TE, and sometimes RB)
        if 'position' in df.columns:
            pos_upper = df['position'].str.upper()
            valid_positions = pos_upper.isin(['WR', 'TE', 'RB', 'FB', 'HB'])
            if valid_positions.sum() > 0:
                df = df[valid_positions]

        # Filter by minimum targets
        if 'targets' in df.columns:
            df = df[df['targets'] >= 10]

        print(f"Found {len(df)} receivers with stats")

        _data_cache[cache_key] = df
        _save_to_file_cache(cache_key, df)

        # Apply position filter if specified
        if position_filter:
            filtered = df[df['position'].str.upper() == position_filter.upper()]
            if len(filtered) > 0:
                return filtered
            else:
                print(f"Warning: No players found for position {position_filter}, returning all receivers")

        return df

    except Exception as e:
        print(f"Error fetching receiving data: {e}")
        import traceback
        traceback.print_exc()
        file_cached = _load_from_file_cache(cache_key)
        if file_cached is not None:
            _data_cache[cache_key] = file_cached
            df = file_cached.copy()
            if position_filter:
                filtered = df[df['position'].str.upper() == position_filter.upper()]
                if len(filtered) > 0:
                    return filtered
            return df
        return _get_sample_receiving_data(position_filter)


def fetch_kicking_stats(season: int = settings.current_season) -> pd.DataFrame:
    """Fetch kicker stats from Pro Football Reference."""
    global _data_cache

    cache_key = f"kicking_{season}"
    if cache_key in _data_cache:
        return _data_cache[cache_key]

    # Try file cache before fetching from network
    file_cached = _load_from_file_cache(cache_key)
    if file_cached is not None:
        _data_cache[cache_key] = file_cached
        return file_cached

    try:
        print(f"Fetching {season} kicking stats from Pro Football Reference...")
        url = f'https://www.pro-football-reference.com/years/{season}/kicking.htm'
        tables = pd.read_html(url)

        if not tables:
            print("No tables found, using sample data")
            return _get_sample_kicking_data()

        df = tables[0]

        # Handle multi-level columns - use same method as other tables for consistency
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[1] if col[0].startswith('Unnamed') else f'{col[0]}_{col[1]}' for col in df.columns]


        # Remove header rows - look for 'Rk' column flexibly
        rk_col = find_column(df, ['Rk'])
        if rk_col:
            df = df[df[rk_col] != 'Rk'].copy()

        # Find player name column - could be 'Player', 'Scoring_Player', etc.
        player_col = find_column(df, ['Player'])
        if player_col:
            df['player_name'] = df[player_col].astype(str).str.replace(r'[*+]', '', regex=True).str.strip()
        else:
            df['player_name'] = 'Unknown'

        # Find team column
        team_col = find_column(df, ['Tm', 'Team'])
        if team_col:
            df['team'] = df[team_col]
        else:
            df['team'] = 'UNK'

        # Find position column
        pos_col = find_column(df, ['Pos', 'Position'])
        if pos_col:
            df['position'] = df[pos_col]
        else:
            # Default to K since this is the kicking table
            df['position'] = 'K'

        # Find games played column
        games_col = find_column(df, ['G', 'Games'])
        if games_col:
            df['games_played'] = pd.to_numeric(df[games_col], errors='coerce').fillna(0)
        else:
            df['games_played'] = 0

        # Try to find FG stats - look more carefully for column patterns
        # FG Made: look for 'Scoring_FGM' first (most specific), then 'FGM'
        fg_made_col = find_column(df, ['Scoring_FGM', 'FGM'])
        if fg_made_col:
            df['fg_made'] = pd.to_numeric(df[fg_made_col], errors='coerce').fillna(0)

        # FG Attempts: look for 'Scoring_FGA' first, then 'FGA'
        fg_att_col = find_column(df, ['Scoring_FGA', 'FGA'])
        if fg_att_col:
            df['fg_attempts'] = pd.to_numeric(df[fg_att_col], errors='coerce').fillna(0)

        # XP Made: look for 'Scoring_XPM' first
        xp_made_col = find_column(df, ['Scoring_XPM', 'XPM'])
        if xp_made_col:
            df['xp_made'] = pd.to_numeric(df[xp_made_col], errors='coerce').fillna(0)

        # XP Attempts: look for 'Scoring_XPA' first
        xp_att_col = find_column(df, ['Scoring_XPA', 'XPA'])
        if xp_att_col:
            df['xp_attempts'] = pd.to_numeric(df[xp_att_col], errors='coerce').fillna(0)

        # Points - Note: PFR kicking table may not have points, would need to calculate
        pts_col = find_column(df, ['Scoring_Pts', 'Pts', 'Points'])
        if pts_col:
            df['total_points'] = pd.to_numeric(df[pts_col], errors='coerce').fillna(0)

        # Long FG: look for 'Scoring_Lng' first
        lng_col = find_column(df, ['Scoring_Lng', 'Lng', 'Long'])
        if lng_col:
            df['long_fg'] = pd.to_numeric(df[lng_col], errors='coerce').fillna(0)

        # Distance-based FG stats - look for FGM (made) columns with distance range
        for col in df.columns:
            if '40-49' in col and 'FGM' in col:
                df['fg_made_40_49'] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            elif ('50+' in col or '50-' in col) and 'FGM' in col:
                df['fg_made_50_plus'] = pd.to_numeric(df[col], errors='coerce').fillna(0)

        # Add player_id
        df['player_id'] = range(1, len(df) + 1)

        # Ensure required columns exist with defaults
        default_cols = {
            'fg_made': 0, 'fg_attempts': 0, 'xp_made': 0, 'xp_attempts': 0,
            'fg_made_40_49': 0, 'fg_made_50_plus': 0, 'long_fg': 0, 'total_points': 0
        }
        for col, default in default_cols.items():
            if col not in df.columns:
                df[col] = default

        # Calculate percentages
        df['fg_pct'] = df.apply(
            lambda x: (x['fg_made'] / max(x['fg_attempts'], 1)) * 100,
            axis=1
        )
        df['xp_pct'] = df.apply(
            lambda x: (x['xp_made'] / max(x['xp_attempts'], 1)) * 100,
            axis=1
        )

        # Filter to kickers only - but be flexible
        if 'position' in df.columns:
            pos_upper = df['position'].astype(str).str.upper()
            k_mask = pos_upper == 'K'
            if k_mask.sum() > 0:
                df = df[k_mask]
            # else: keep all players with FG attempts (they're likely kickers)

        # Filter by minimum FG attempts
        df = df[df['fg_attempts'] >= 5]

        # Convert games_played
        if 'games_played' in df.columns:
            df['games_played'] = pd.to_numeric(df['games_played'], errors='coerce').fillna(0).astype(int)

        print(f"Found {len(df)} kickers with stats")

        _data_cache[cache_key] = df
        _save_to_file_cache(cache_key, df)
        return df

    except Exception as e:
        print(f"Error fetching kicking data: {e}")
        import traceback
        traceback.print_exc()
        file_cached = _load_from_file_cache(cache_key)
        if file_cached is not None:
            _data_cache[cache_key] = file_cached
            return file_cached
        return _get_sample_kicking_data()


# Sample data functions for fallback
def _get_sample_defensive_data() -> pd.DataFrame:
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
    ]
    return pd.DataFrame(sample_players)


def _get_sample_passing_data() -> pd.DataFrame:
    """Return sample QB data for development/testing."""
    sample_players = [
        {"player_id": 1, "player_name": "Patrick Mahomes", "position": "QB", "team": "KC",
         "games_played": 17, "pass_attempts": 648, "completions": 401, "completion_pct": 67.2,
         "pass_yards": 4839, "pass_tds": 41, "interceptions": 12, "passer_rating": 105.3,
         "yards_per_attempt": 7.5, "sacks": 27, "first_downs": 221,
         "int_rate_inv": 98.1, "sack_rate_inv": 95.8, "fumbles_inv": 100},
        {"player_id": 2, "player_name": "Josh Allen", "position": "QB", "team": "BUF",
         "games_played": 17, "pass_attempts": 573, "completions": 385, "completion_pct": 66.5,
         "pass_yards": 4306, "pass_tds": 35, "interceptions": 10, "passer_rating": 101.2,
         "yards_per_attempt": 7.5, "sacks": 33, "first_downs": 198,
         "int_rate_inv": 98.3, "sack_rate_inv": 94.2, "fumbles_inv": 95},
        {"player_id": 3, "player_name": "Lamar Jackson", "position": "QB", "team": "BAL",
         "games_played": 16, "pass_attempts": 457, "completions": 307, "completion_pct": 67.2,
         "pass_yards": 3678, "pass_tds": 24, "interceptions": 7, "passer_rating": 102.7,
         "yards_per_attempt": 8.0, "sacks": 25, "first_downs": 175,
         "int_rate_inv": 98.5, "sack_rate_inv": 94.5, "fumbles_inv": 90},
    ]
    return pd.DataFrame(sample_players)


def _get_sample_rushing_data() -> pd.DataFrame:
    """Return sample RB data for development/testing."""
    sample_players = [
        {"player_id": 1, "player_name": "Christian McCaffrey", "position": "RB", "team": "SF",
         "games_played": 16, "rush_attempts": 272, "rush_yards": 1459, "yards_per_carry": 5.4,
         "rush_tds": 14, "first_downs": 78, "longest_rush": 65, "fumbles": 2,
         "receptions": 67, "rec_yards": 564, "rec_tds": 7, "targets": 83,
         "touches": 339, "yards_per_touch": 5.97, "total_tds": 21, "success_rate": 55},
        {"player_id": 2, "player_name": "Derrick Henry", "position": "RB", "team": "TEN",
         "games_played": 17, "rush_attempts": 349, "rush_yards": 1990, "yards_per_carry": 5.7,
         "rush_tds": 17, "first_downs": 98, "longest_rush": 75, "fumbles": 1,
         "receptions": 28, "rec_yards": 214, "rec_tds": 1, "targets": 34,
         "touches": 377, "yards_per_touch": 5.85, "total_tds": 18, "success_rate": 52},
        {"player_id": 3, "player_name": "Saquon Barkley", "position": "RB", "team": "NYG",
         "games_played": 16, "rush_attempts": 247, "rush_yards": 962, "yards_per_carry": 3.9,
         "rush_tds": 6, "first_downs": 55, "longest_rush": 36, "fumbles": 3,
         "receptions": 41, "rec_yards": 280, "rec_tds": 4, "targets": 54,
         "touches": 288, "yards_per_touch": 4.31, "total_tds": 10, "success_rate": 45},
    ]
    return pd.DataFrame(sample_players)


def _get_sample_receiving_data(position_filter: Optional[str] = None) -> pd.DataFrame:
    """Return sample WR/TE data for development/testing."""
    sample_players = [
        {"player_id": 1, "player_name": "Tyreek Hill", "position": "WR", "team": "MIA",
         "games_played": 16, "targets": 170, "receptions": 119, "catch_rate": 70.0,
         "rec_yards": 1799, "yards_per_reception": 15.1, "yards_per_target": 10.6,
         "rec_tds": 13, "first_downs": 78, "longest_rec": 69, "yards_after_catch": 650, "fumbles": 1},
        {"player_id": 2, "player_name": "CeeDee Lamb", "position": "WR", "team": "DAL",
         "games_played": 17, "targets": 181, "receptions": 135, "catch_rate": 74.6,
         "rec_yards": 1749, "yards_per_reception": 13.0, "yards_per_target": 9.7,
         "rec_tds": 12, "first_downs": 85, "longest_rec": 55, "yards_after_catch": 580, "fumbles": 0},
        {"player_id": 3, "player_name": "Travis Kelce", "position": "TE", "team": "KC",
         "games_played": 17, "targets": 121, "receptions": 93, "catch_rate": 76.9,
         "rec_yards": 984, "yards_per_reception": 10.6, "yards_per_target": 8.1,
         "rec_tds": 5, "first_downs": 55, "longest_rec": 42, "yards_after_catch": 380, "fumbles": 0},
        {"player_id": 4, "player_name": "TJ Hockenson", "position": "TE", "team": "MIN",
         "games_played": 15, "targets": 109, "receptions": 95, "catch_rate": 87.2,
         "rec_yards": 960, "yards_per_reception": 10.1, "yards_per_target": 8.8,
         "rec_tds": 5, "first_downs": 52, "longest_rec": 35, "yards_after_catch": 320, "fumbles": 1},
    ]
    df = pd.DataFrame(sample_players)
    if position_filter:
        df = df[df['position'].str.upper() == position_filter.upper()]
    return df


def _get_sample_kicking_data() -> pd.DataFrame:
    """Return sample kicker data for development/testing."""
    sample_players = [
        {"player_id": 1, "player_name": "Justin Tucker", "position": "K", "team": "BAL",
         "games_played": 17, "fg_made": 32, "fg_attempts": 35, "fg_pct": 91.4,
         "fg_made_40_49": 8, "fg_made_50_plus": 5, "long_fg": 57,
         "xp_made": 42, "xp_attempts": 42, "xp_pct": 100.0, "total_points": 138},
        {"player_id": 2, "player_name": "Harrison Butker", "position": "K", "team": "KC",
         "games_played": 17, "fg_made": 33, "fg_attempts": 36, "fg_pct": 91.7,
         "fg_made_40_49": 10, "fg_made_50_plus": 4, "long_fg": 54,
         "xp_made": 51, "xp_attempts": 52, "xp_pct": 98.1, "total_points": 150},
        {"player_id": 3, "player_name": "Jake Elliott", "position": "K", "team": "PHI",
         "games_played": 17, "fg_made": 30, "fg_attempts": 34, "fg_pct": 88.2,
         "fg_made_40_49": 7, "fg_made_50_plus": 6, "long_fg": 59,
         "xp_made": 55, "xp_attempts": 55, "xp_pct": 100.0, "total_points": 145},
    ]
    return pd.DataFrame(sample_players)


def fetch_stats_for_position_group(position_group: str, season: int = settings.current_season) -> pd.DataFrame:
    """Fetch stats for a specific position group."""
    config = get_position_group(position_group)
    data_source = config["data_source"]

    if data_source == "defense":
        return fetch_defensive_stats(season)
    elif data_source == "passing":
        return fetch_passing_stats(season)
    elif data_source == "rushing":
        return fetch_rushing_stats(season)
    elif data_source == "receiving":
        return fetch_receiving_stats(season, position_group if position_group in ["WR", "TE"] else None)
    elif data_source == "kicking":
        return fetch_kicking_stats(season)
    else:
        raise ValueError(f"Unknown data source: {data_source}")


def process_player_rankings(
    data: Optional[pd.DataFrame] = None,
    min_games: int = 1,
    position_filter: Optional[str] = None,
    weights: Optional[Dict[str, float]] = None,
    position_group: str = "DEF",
) -> List[Dict[str, Any]]:
    """
    Process player data and calculate rankings for any position group.

    Args:
        data: DataFrame with player stats (fetches if None)
        min_games: Minimum games played filter
        position_filter: Optional sub-position filter (e.g., 'DL' within 'DEF')
        weights: Optional category weights (uses config defaults if None)
        position_group: Position group ID (DEF, QB, RB, WR, TE, K)

    Returns:
        List of player rankings sorted by overall score
    """
    group_config = get_position_group(position_group)
    categories = get_categories_for_group(position_group)
    log_scale_stats = get_log_scale_stats(position_group)

    if data is None:
        data = fetch_stats_for_position_group(position_group)

    # Make a copy to avoid modifying original
    data = data.copy()

    # Filter by minimum games
    if "games_played" in data.columns:
        data = data[data["games_played"] >= min_games]

    # Filter by sub-position (for defensive players)
    if position_filter and position_filter != "All" and position_group == "DEF":
        if "position" in data.columns:
            data = data[data["position"].apply(map_position) == position_filter]

    if data.empty:
        return []

    # Get stat columns from config
    stat_cols = group_config["stat_columns"]

    # Ensure all stat columns exist
    for col in stat_cols:
        if col not in data.columns:
            data[col] = 0.0

    all_stats = data[stat_cols].to_dict("records")

    # Calculate raw z-scores for all categories
    raw_category_scores = calculate_raw_category_z_scores(
        all_stats, categories, log_scale_stats
    )

    # Calculate raw overall z-scores
    category_weights = weights or get_category_weights(position_group)
    num_players = len(all_stats)
    raw_overall_scores = []
    for i in range(num_players):
        raw_overall = sum(
            raw_category_scores[cat["id"]][i] * category_weights.get(cat["id"], 0.25)
            for cat in categories
            if cat["id"] in raw_category_scores
        )
        raw_overall_scores.append(raw_overall)

    # Normalize all scores to 60-100
    normalized_overall = normalize_scores_to_range(raw_overall_scores)
    normalized_category_scores = {
        cat_id: normalize_scores_to_range(scores)
        for cat_id, scores in raw_category_scores.items()
    }

    # Build player records
    rankings = []
    data_rows = list(data.iterrows())
    for i, (idx, row) in enumerate(data_rows):
        player_stats = {col: float(row.get(col, 0.0)) for col in stat_cols}

        # Get normalized category scores for this player
        category_scores = {
            cat["id"]: normalized_category_scores[cat["id"]][i]
            for cat in categories
            if cat["id"] in normalized_category_scores
        }

        overall = normalized_overall[i]

        player_id = row.get("player_id", str(idx))
        try:
            player_id_int = abs(hash(str(player_id))) % 1000000
        except:
            player_id_int = idx + 1

        # Determine display position
        raw_position = row.get("position", position_group)
        if position_group == "DEF":
            display_position = map_position(raw_position)
        else:
            display_position = raw_position

        rankings.append({
            "id": player_id_int,
            "name": row.get("player_name", row.get("name", "Unknown")),
            "team": row.get("team", "UNK"),
            "position": display_position,
            "position_group": position_group,
            "games_played": int(row.get("games_played", row.get("games", 0))),
            "overall_score": round(overall, 1),
            "category_scores": {k: round(v, 1) for k, v in category_scores.items()},
            "stats": player_stats,
        })

    # Sort by overall score descending
    rankings.sort(key=lambda x: x["overall_score"], reverse=True)

    return rankings
