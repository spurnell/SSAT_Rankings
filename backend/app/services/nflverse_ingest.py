"""
NFL data ingestion service.

Fetches NFL data from nfl_data_py and writes to the rankings SQLite database.
Called via CLI command, not on every API request.

Uses:
- nfl.import_players() for player roster
- nfl.import_seasonal_data() for offensive stats (passing, rushing, receiving)
- nfl.import_pbp_data() for defensive and kicking stats (aggregated from play-by-play)
"""

import nfl_data_py as nfl
import pandas as pd
import numpy as np
from datetime import datetime

from app.db.database import RankingsSessionLocal, init_rankings_db
from app.db.stats_models import Player, PlayerSeasonStats, IngestionLog


# Map nflverse positions to our position groups
POSITION_TO_GROUP = {
    # Defensive
    "DE": "DEF", "DT": "DEF", "NT": "DEF",
    "OLB": "DEF", "ILB": "DEF", "MLB": "DEF", "LB": "DEF",
    "CB": "DEF", "FS": "DEF", "SS": "DEF", "S": "DEF", "DB": "DEF",
    "EDGE": "DEF", "SAF": "DEF", "DL": "DEF",
    # Offensive
    "QB": "QB",
    "RB": "RB", "FB": "RB", "HB": "RB",
    "WR": "WR",
    "TE": "TE",
    # Special teams
    "K": "K",
}


def _log_ingestion(session, season, data_type, rows, status, error=None, started_at=None):
    """Log an ingestion run."""
    log = IngestionLog(
        season=season,
        data_type=data_type,
        rows_ingested=rows,
        started_at=started_at or datetime.utcnow(),
        completed_at=datetime.utcnow(),
        status=status,
        error_message=error,
    )
    session.add(log)
    session.commit()


def ingest_players():
    """Fetch player roster from nflverse and upsert into players table."""
    init_rankings_db()
    session = RankingsSessionLocal()
    started = datetime.utcnow()

    try:
        print("Fetching player roster from nflverse...")
        players_df = nfl.import_players()

        # Filter to players with a gsis_id and relevant position
        players_df = players_df.dropna(subset=["gsis_id", "position"])
        players_df = players_df[players_df["position"].isin(POSITION_TO_GROUP.keys())]

        count = 0
        for _, row in players_df.iterrows():
            gsis_id = row["gsis_id"]
            position = row["position"]
            position_group = POSITION_TO_GROUP.get(position, "")
            if not position_group:
                continue

            existing = session.get(Player, gsis_id)
            if existing:
                existing.display_name = row.get("display_name", existing.display_name)
                existing.position = position
                existing.position_group = position_group
                existing.team = row.get("latest_team") or existing.team
                existing.headshot_url = row.get("headshot") or existing.headshot_url
            else:
                session.add(Player(
                    gsis_id=gsis_id,
                    display_name=row.get("display_name", "Unknown"),
                    position=position,
                    position_group=position_group,
                    team=row.get("latest_team"),
                    headshot_url=row.get("headshot"),
                ))
            count += 1

        session.commit()
        print(f"Ingested {count} players.")
        _log_ingestion(session, 0, "players", count, "success", started_at=started)
        return count

    except Exception as e:
        session.rollback()
        print(f"Error ingesting players: {e}")
        _log_ingestion(session, 0, "players", 0, "error", str(e), started_at=started)
        raise
    finally:
        session.close()


def _aggregate_defensive_stats(pbp: pd.DataFrame) -> pd.DataFrame:
    """Aggregate play-by-play data into per-player defensive season stats."""
    frames = {}

    # Solo tackles
    solo_dfs = []
    for col in ["solo_tackle_1_player_id", "solo_tackle_2_player_id"]:
        if col in pbp.columns:
            df = pbp[[col, "season", "game_id"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            solo_dfs.append(df)
    if solo_dfs:
        solo = pd.concat(solo_dfs)
        frames["solo_tackles"] = solo.groupby(["player_id", "season"]).size().reset_index(name="solo_tackles")

    # Assist tackles
    assist_dfs = []
    for i in range(1, 5):
        col = f"assist_tackle_{i}_player_id"
        if col in pbp.columns:
            df = pbp[[col, "season", "game_id"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            assist_dfs.append(df)
    if assist_dfs:
        assists = pd.concat(assist_dfs)
        frames["assists"] = assists.groupby(["player_id", "season"]).size().reset_index(name="assists")

    # Sacks: full sacks (1.0) + half sacks (0.5)
    sack_dfs = []
    if "sack_player_id" in pbp.columns:
        full_sacks = pbp[pbp["sack"] == 1][["sack_player_id", "season", "game_id"]].rename(
            columns={"sack_player_id": "player_id"}
        ).dropna(subset=["player_id"])
        full_sacks["sack_value"] = 1.0
        sack_dfs.append(full_sacks[["player_id", "season", "sack_value"]])
    for col in ["half_sack_1_player_id", "half_sack_2_player_id"]:
        if col in pbp.columns:
            half = pbp[pbp["sack"] == 1][[col, "season"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            half["sack_value"] = 0.5
            sack_dfs.append(half[["player_id", "season", "sack_value"]])
    if sack_dfs:
        sacks = pd.concat(sack_dfs)
        frames["def_sacks"] = sacks.groupby(["player_id", "season"])["sack_value"].sum().reset_index(name="def_sacks")

    # QB hits
    qbhit_dfs = []
    for col in ["qb_hit_1_player_id", "qb_hit_2_player_id"]:
        if col in pbp.columns:
            df = pbp[pbp["qb_hit"] == 1][[col, "season"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            qbhit_dfs.append(df)
    if qbhit_dfs:
        qbhits = pd.concat(qbhit_dfs)
        frames["qb_hits"] = qbhits.groupby(["player_id", "season"]).size().reset_index(name="qb_hits")

    # Tackles for loss
    tfl_dfs = []
    for col in ["tackle_for_loss_1_player_id", "tackle_for_loss_2_player_id"]:
        if col in pbp.columns:
            df = pbp[pbp["tackled_for_loss"] == 1][[col, "season"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            tfl_dfs.append(df)
    if tfl_dfs:
        tfl = pd.concat(tfl_dfs)
        frames["tackles_for_loss"] = tfl.groupby(["player_id", "season"]).size().reset_index(name="tackles_for_loss")

    # Passes defended
    pd_dfs = []
    for col in ["pass_defense_1_player_id", "pass_defense_2_player_id"]:
        if col in pbp.columns:
            df = pbp[[col, "season"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            pd_dfs.append(df)
    if pd_dfs:
        passes_def = pd.concat(pd_dfs)
        frames["passes_defended"] = passes_def.groupby(["player_id", "season"]).size().reset_index(name="passes_defended")

    # Interceptions
    if "interception_player_id" in pbp.columns:
        ints = pbp[pbp["interception"] == 1][["interception_player_id", "season"]].rename(
            columns={"interception_player_id": "player_id"}
        ).dropna(subset=["player_id"])
        frames["def_interceptions"] = ints.groupby(["player_id", "season"]).size().reset_index(name="def_interceptions")

    # Forced fumbles
    ff_dfs = []
    for col in ["forced_fumble_player_1_player_id", "forced_fumble_player_2_player_id"]:
        if col in pbp.columns:
            df = pbp[pbp["fumble_forced"] == 1][[col, "season"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            ff_dfs.append(df)
    if ff_dfs:
        ff = pd.concat(ff_dfs)
        frames["forced_fumbles"] = ff.groupby(["player_id", "season"]).size().reset_index(name="forced_fumbles")

    # Fumble recoveries (opponent only — recovery team != possession team)
    fr_dfs = []
    for i in [1, 2]:
        pid_col = f"fumble_recovery_{i}_player_id"
        team_col = f"fumble_recovery_{i}_team"
        if pid_col in pbp.columns and team_col in pbp.columns:
            df = pbp[pbp["fumble"] == 1][[pid_col, team_col, "posteam", "season"]].copy()
            df = df.rename(columns={pid_col: "player_id", team_col: "rec_team"})
            df = df.dropna(subset=["player_id"])
            # Only count recoveries where the recovering team is NOT the team with possession
            df = df[df["rec_team"] != df["posteam"]]
            fr_dfs.append(df[["player_id", "season"]])
    if fr_dfs:
        fr = pd.concat(fr_dfs)
        frames["fumble_recoveries"] = fr.groupby(["player_id", "season"]).size().reset_index(name="fumble_recoveries")

    # Defensive TDs (interception return TD or fumble recovery TD)
    td_dfs = []
    if "td_player_id" in pbp.columns:
        # INT return TDs
        int_tds = pbp[(pbp["interception"] == 1) & (pbp["touchdown"] == 1)][
            ["td_player_id", "season"]
        ].rename(columns={"td_player_id": "player_id"}).dropna(subset=["player_id"])
        td_dfs.append(int_tds)
        # Fumble return TDs
        fum_tds = pbp[(pbp["fumble"] == 1) & (pbp["touchdown"] == 1)][
            ["td_player_id", "season"]
        ].rename(columns={"td_player_id": "player_id"}).dropna(subset=["player_id"])
        td_dfs.append(fum_tds)
    if td_dfs:
        def_tds = pd.concat(td_dfs)
        frames["defensive_tds"] = def_tds.groupby(["player_id", "season"]).size().reset_index(name="defensive_tds")

    # Games played (distinct games where player appears in any defensive stat column)
    game_dfs = []
    all_def_pid_cols = [
        "solo_tackle_1_player_id", "solo_tackle_2_player_id",
        "assist_tackle_1_player_id", "assist_tackle_2_player_id",
        "assist_tackle_3_player_id", "assist_tackle_4_player_id",
        "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id",
        "qb_hit_1_player_id", "qb_hit_2_player_id",
        "tackle_for_loss_1_player_id", "tackle_for_loss_2_player_id",
        "pass_defense_1_player_id", "pass_defense_2_player_id",
        "interception_player_id",
        "forced_fumble_player_1_player_id", "forced_fumble_player_2_player_id",
    ]
    for col in all_def_pid_cols:
        if col in pbp.columns:
            df = pbp[[col, "season", "game_id"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            game_dfs.append(df[["player_id", "season", "game_id"]])
    if game_dfs:
        all_games = pd.concat(game_dfs).drop_duplicates()
        frames["games_played"] = all_games.groupby(["player_id", "season"])["game_id"].nunique().reset_index(name="games_played")

    # Merge all stat frames together
    if not frames:
        return pd.DataFrame(columns=["player_id", "season"])

    result = None
    for key, df in frames.items():
        if result is None:
            result = df
        else:
            result = result.merge(df, on=["player_id", "season"], how="outer")

    # Fill NaN with 0 for count stats
    fill_cols = [c for c in result.columns if c not in ("player_id", "season")]
    result[fill_cols] = result[fill_cols].fillna(0)

    # Compute total tackles
    if "solo_tackles" in result.columns and "assists" in result.columns:
        result["tackles"] = result["solo_tackles"] + result["assists"]

    return result


def _extract_season_teams(pbp: pd.DataFrame, seasons: list[int]) -> dict:
    """Extract per-player per-season team assignments.

    Returns dict of {(player_id, season): team_abbr}.
    Uses weekly data for offensive players and PBP for defensive/kicking players.
    """
    team_map = {}

    # --- Offensive players: from import_weekly_data (has recent_team per game) ---
    try:
        weekly = nfl.import_weekly_data(seasons)
        if "recent_team" in weekly.columns and "player_id" in weekly.columns:
            weekly = weekly[weekly["season_type"] == "REG"] if "season_type" in weekly.columns else weekly
            weekly = weekly.dropna(subset=["player_id", "recent_team"])
            # Take mode (most common team) per player per season
            off_teams = weekly.groupby(["player_id", "season"])["recent_team"].agg(
                lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]
            ).reset_index()
            for _, row in off_teams.iterrows():
                team_map[(row["player_id"], int(row["season"]))] = row["recent_team"]
    except Exception as e:
        print(f"  Warning: could not fetch weekly data for teams: {e}")

    # --- Defensive players: from PBP defteam ---
    def_pid_cols = [
        "solo_tackle_1_player_id", "solo_tackle_2_player_id",
        "assist_tackle_1_player_id", "assist_tackle_2_player_id",
        "sack_player_id", "half_sack_1_player_id", "half_sack_2_player_id",
        "interception_player_id",
        "pass_defense_1_player_id", "pass_defense_2_player_id",
        "forced_fumble_player_1_player_id", "forced_fumble_player_2_player_id",
        "qb_hit_1_player_id", "qb_hit_2_player_id",
        "tackle_for_loss_1_player_id", "tackle_for_loss_2_player_id",
    ]
    def_dfs = []
    for col in def_pid_cols:
        if col in pbp.columns:
            df = pbp[[col, "defteam", "season"]].rename(columns={col: "player_id"}).dropna(subset=["player_id"])
            def_dfs.append(df[["player_id", "defteam", "season"]])
    if def_dfs:
        all_def = pd.concat(def_dfs)
        def_teams = all_def.groupby(["player_id", "season"])["defteam"].agg(
            lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]
        ).reset_index()
        for _, row in def_teams.iterrows():
            key = (row["player_id"], int(row["season"]))
            if key not in team_map:  # Don't overwrite offensive team
                team_map[key] = row["defteam"]

    # --- Kickers: from PBP posteam on kicking plays ---
    if "kicker_player_id" in pbp.columns:
        kick_plays = pbp[
            (pbp["field_goal_attempt"] == 1) | (pbp["extra_point_attempt"] == 1)
        ][["kicker_player_id", "posteam", "season"]].copy()
        kick_plays = kick_plays.rename(columns={"kicker_player_id": "player_id"}).dropna(subset=["player_id"])
        if not kick_plays.empty:
            kick_teams = kick_plays.groupby(["player_id", "season"])["posteam"].agg(
                lambda x: x.mode().iloc[0] if len(x.mode()) > 0 else x.iloc[0]
            ).reset_index()
            for _, row in kick_teams.iterrows():
                key = (row["player_id"], int(row["season"]))
                if key not in team_map:
                    team_map[key] = row["posteam"]

    return team_map


def _aggregate_longest_plays(pbp: pd.DataFrame) -> pd.DataFrame:
    """Extract longest rush and longest reception per player per season from PBP."""
    frames = []

    # Longest rush
    if "rusher_player_id" in pbp.columns:
        rushes = pbp[(pbp["play_type"] == "run") & (pbp["rusher_player_id"].notna())][
            ["rusher_player_id", "season", "rushing_yards"]
        ].copy()
        rushes = rushes.rename(columns={"rusher_player_id": "player_id"})
        rushes["rushing_yards"] = pd.to_numeric(rushes["rushing_yards"], errors="coerce").fillna(0)
        longest_rush = rushes.groupby(["player_id", "season"])["rushing_yards"].max().reset_index(name="longest_rush")
        frames.append(longest_rush)

    # Longest reception
    if "receiver_player_id" in pbp.columns:
        recs = pbp[(pbp["play_type"] == "pass") & (pbp["complete_pass"] == 1) & (pbp["receiver_player_id"].notna())][
            ["receiver_player_id", "season", "yards_gained"]
        ].copy()
        recs = recs.rename(columns={"receiver_player_id": "player_id"})
        recs["yards_gained"] = pd.to_numeric(recs["yards_gained"], errors="coerce").fillna(0)
        longest_rec = recs.groupby(["player_id", "season"])["yards_gained"].max().reset_index(name="longest_reception")
        frames.append(longest_rec)

    if not frames:
        return pd.DataFrame(columns=["player_id", "season"])

    result = frames[0]
    for df in frames[1:]:
        result = result.merge(df, on=["player_id", "season"], how="outer")
    result = result.fillna(0)
    return result


def _aggregate_offensive_stats(pbp: pd.DataFrame) -> pd.DataFrame:
    """Aggregate play-by-play data into per-player offensive season stats.

    Used as a fallback when import_seasonal_data is unavailable (e.g., 2025 season).
    """
    rows = []

    # --- Passing stats (keyed by passer_player_id) ---
    pass_plays = pbp[pbp["play_type"].isin(["pass", "qb_spike"])].copy()
    if not pass_plays.empty and "passer_player_id" in pass_plays.columns:
        pass_agg = pass_plays.groupby(["passer_player_id", "season"]).agg(
            completions=("complete_pass", "sum"),
            attempts=("pass_attempt", "sum"),
            passing_yards=("passing_yards", "sum"),
            passing_tds=("pass_touchdown", "sum"),
            interceptions=("interception", "sum"),
            passing_first_downs=("first_down_pass", "sum"),
            pass_games=("game_id", "nunique"),
        ).reset_index().rename(columns={"passer_player_id": "player_id"})
        rows.append(pass_agg)

    # Sacks (attributed to passer)
    sack_plays = pbp[pbp["sack"] == 1].copy()
    if not sack_plays.empty and "passer_player_id" in sack_plays.columns:
        sack_agg = sack_plays.groupby(["passer_player_id", "season"]).agg(
            sacks=("sack", "sum"),
            sack_yards=("yards_gained", lambda x: -x.sum()),  # sack yards are negative
        ).reset_index().rename(columns={"passer_player_id": "player_id"})
        rows.append(sack_agg)

    # Sack fumbles (attributed to passer)
    sack_fumble_plays = pbp[(pbp["sack"] == 1) & (pbp["fumble"] == 1)].copy()
    if not sack_fumble_plays.empty and "passer_player_id" in sack_fumble_plays.columns:
        sf_agg = sack_fumble_plays.groupby(["passer_player_id", "season"]).size().reset_index(name="sack_fumbles")
        sf_agg = sf_agg.rename(columns={"passer_player_id": "player_id"})
        rows.append(sf_agg)

    # --- Rushing stats (keyed by rusher_player_id) ---
    rush_plays = pbp[pbp["play_type"] == "run"].copy()
    if not rush_plays.empty and "rusher_player_id" in rush_plays.columns:
        rush_agg = rush_plays.groupby(["rusher_player_id", "season"]).agg(
            carries=("rush_attempt", "sum"),
            rushing_yards=("rushing_yards", "sum"),
            rushing_tds=("rush_touchdown", "sum"),
            rushing_first_downs=("first_down_rush", "sum"),
            rush_games=("game_id", "nunique"),
        ).reset_index().rename(columns={"rusher_player_id": "player_id"})
        rows.append(rush_agg)

    # Rushing fumbles
    rush_fumble_plays = pbp[(pbp["play_type"] == "run") & (pbp["fumble"] == 1)].copy()
    if not rush_fumble_plays.empty and "rusher_player_id" in rush_fumble_plays.columns:
        rf_agg = rush_fumble_plays.groupby(["rusher_player_id", "season"]).size().reset_index(name="rushing_fumbles")
        rf_agg = rf_agg.rename(columns={"rusher_player_id": "player_id"})
        rows.append(rf_agg)

    # --- Receiving stats (keyed by receiver_player_id) ---
    recv_plays = pbp[(pbp["play_type"] == "pass") & (pbp["receiver_player_id"].notna())].copy()
    if not recv_plays.empty:
        # Targets = all pass plays aimed at this receiver
        target_agg = recv_plays.groupby(["receiver_player_id", "season"]).agg(
            targets=("pass_attempt", "sum"),
            receptions=("complete_pass", "sum"),
            receiving_yards=("yards_gained", lambda x: x[recv_plays.loc[x.index, "complete_pass"] == 1].sum()),
            receiving_tds=("pass_touchdown", "sum"),
            receiving_first_downs=("first_down_pass", "sum"),
            receiving_yards_after_catch=("yards_after_catch", "sum"),
            recv_games=("game_id", "nunique"),
        ).reset_index().rename(columns={"receiver_player_id": "player_id"})
        rows.append(target_agg)

    # Receiving fumbles
    recv_fumble_plays = pbp[(pbp["play_type"] == "pass") & (pbp["complete_pass"] == 1) & (pbp["fumble"] == 1) & (pbp["receiver_player_id"].notna())].copy()
    if not recv_fumble_plays.empty:
        recf_agg = recv_fumble_plays.groupby(["receiver_player_id", "season"]).size().reset_index(name="receiving_fumbles")
        recf_agg = recf_agg.rename(columns={"receiver_player_id": "player_id"})
        rows.append(recf_agg)

    if not rows:
        return pd.DataFrame(columns=["player_id", "season"])

    # Merge all frames
    result = rows[0]
    for df in rows[1:]:
        result = result.merge(df, on=["player_id", "season"], how="outer")

    fill_cols = [c for c in result.columns if c not in ("player_id", "season")]
    result[fill_cols] = result[fill_cols].fillna(0)

    # Compute games played as max across pass/rush/recv games
    game_cols = [c for c in result.columns if c.endswith("_games")]
    if game_cols:
        result["games"] = result[game_cols].max(axis=1).astype(int)
        result = result.drop(columns=game_cols)

    return result


def _aggregate_kicking_stats(pbp: pd.DataFrame) -> pd.DataFrame:
    """Aggregate play-by-play data into per-player kicking season stats."""
    if "kicker_player_id" not in pbp.columns:
        return pd.DataFrame(columns=["player_id", "season"])

    # Field goal attempts
    fg_plays = pbp[pbp["field_goal_attempt"] == 1][
        ["kicker_player_id", "season", "game_id", "field_goal_result", "kick_distance"]
    ].copy()
    fg_plays = fg_plays.rename(columns={"kicker_player_id": "player_id"})
    fg_plays = fg_plays.dropna(subset=["player_id"])

    if fg_plays.empty:
        return pd.DataFrame(columns=["player_id", "season"])

    fg_plays["is_made"] = (fg_plays["field_goal_result"] == "made").astype(int)
    fg_plays["kick_distance"] = pd.to_numeric(fg_plays["kick_distance"], errors="coerce").fillna(0)
    fg_plays["is_made_40_49"] = ((fg_plays["is_made"] == 1) & (fg_plays["kick_distance"] >= 40) & (fg_plays["kick_distance"] <= 49)).astype(int)
    fg_plays["is_made_50_plus"] = ((fg_plays["is_made"] == 1) & (fg_plays["kick_distance"] >= 50)).astype(int)

    fg_agg = fg_plays.groupby(["player_id", "season"]).agg(
        fg_attempts=("is_made", "count"),
        fg_made=("is_made", "sum"),
        fg_made_40_49=("is_made_40_49", "sum"),
        fg_made_50_plus=("is_made_50_plus", "sum"),
        long_fg=("kick_distance", "max"),
    ).reset_index()

    # Extra point attempts
    xp_plays = pbp[pbp["extra_point_attempt"] == 1][
        ["kicker_player_id", "season", "game_id", "extra_point_result"]
    ].copy()
    xp_plays = xp_plays.rename(columns={"kicker_player_id": "player_id"})
    xp_plays = xp_plays.dropna(subset=["player_id"])

    xp_agg = pd.DataFrame(columns=["player_id", "season", "xp_attempts", "xp_made"])
    if not xp_plays.empty:
        xp_plays["is_good"] = (xp_plays["extra_point_result"] == "good").astype(int)
        xp_agg = xp_plays.groupby(["player_id", "season"]).agg(
            xp_attempts=("is_good", "count"),
            xp_made=("is_good", "sum"),
        ).reset_index()

    # Games played
    kick_plays = pbp[
        (pbp["field_goal_attempt"] == 1) | (pbp["extra_point_attempt"] == 1)
    ][["kicker_player_id", "season", "game_id"]].copy()
    kick_plays = kick_plays.rename(columns={"kicker_player_id": "player_id"}).dropna(subset=["player_id"])
    games = kick_plays.groupby(["player_id", "season"])["game_id"].nunique().reset_index(name="games_played")

    # Merge
    result = fg_agg.merge(xp_agg, on=["player_id", "season"], how="outer")
    result = result.merge(games, on=["player_id", "season"], how="outer")

    fill_cols = [c for c in result.columns if c not in ("player_id", "season")]
    result[fill_cols] = result[fill_cols].fillna(0)

    # Compute kicking points
    result["kicking_points"] = result["fg_made"] * 3 + result["xp_made"]

    return result


def ingest_all_stats(seasons: list[int]):
    """
    Fetch all player stats and write to database.

    Uses:
    - import_seasonal_data() for offensive stats (passing, rushing, receiving)
    - import_pbp_data() for defensive and kicking stats
    """
    init_rankings_db()
    session = RankingsSessionLocal()
    started = datetime.utcnow()

    try:
        # --- Step 1: Fetch PBP data (needed for defense, kicking, and possibly offense) ---
        print(f"Fetching play-by-play data for {seasons}...")
        pbp = nfl.import_pbp_data(seasons, downcast=True)
        # Filter to regular season
        pbp = pbp[pbp["season_type"] == "REG"]
        print(f"  Got {len(pbp)} regular season plays.")

        # --- Step 2: Offensive stats ---
        # Try import_seasonal_data first (faster, pre-aggregated)
        # Fall back to PBP aggregation if unavailable (e.g., current season)
        try:
            print(f"Fetching pre-aggregated seasonal data for {seasons}...")
            offensive = nfl.import_seasonal_data(seasons, s_type="REG")
            # Deduplicate by player_id + season (players traded mid-season may appear twice)
            numeric_cols = offensive.select_dtypes(include=[np.number]).columns.tolist()
            agg_dict = {c: "sum" for c in numeric_cols if c not in ("season",)}
            offensive = offensive.groupby(["player_id", "season"], as_index=False).agg(agg_dict)
            print(f"  Got {len(offensive)} offensive player-season rows.")
        except Exception as e:
            print(f"  Seasonal data unavailable ({e}), aggregating from PBP...")
            offensive = _aggregate_offensive_stats(pbp)
            print(f"  Got {len(offensive)} offensive player-season rows from PBP.")

        # Extract longest rush and longest reception from PBP
        print("Extracting per-season team assignments...")
        team_map = _extract_season_teams(pbp, seasons)
        print(f"  Got team assignments for {len(team_map)} player-seasons.")

        print("Extracting longest rush/reception from PBP...")
        longest_plays = _aggregate_longest_plays(pbp)

        print("Aggregating defensive stats from PBP...")
        defensive = _aggregate_defensive_stats(pbp)
        print(f"  Got {len(defensive)} defensive player-season rows.")

        print("Aggregating kicking stats from PBP...")
        kicking = _aggregate_kicking_stats(pbp)
        print(f"  Got {len(kicking)} kicking player-season rows.")

        # Free PBP memory
        del pbp

        # --- Step 3: Write to database ---
        print("Writing stats to database...")
        count = 0

        # Process offensive stats
        for _, row in offensive.iterrows():
            pid = row.get("player_id")
            if not pid or pd.isna(pid):
                continue
            season_val = int(row["season"])

            player = session.get(Player, pid)
            if not player:
                continue

            games = int(row.get("games", 0))
            if games == 0:
                continue

            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=pid, season=season_val
            ).first()
            if not existing:
                existing = PlayerSeasonStats(gsis_id=pid, season=season_val)
                session.add(existing)

            existing.games_played = games
            existing.team = team_map.get((pid, season_val))

            # Passing
            existing.completions = _safe(row, "completions")
            existing.attempts = _safe(row, "attempts")
            existing.passing_yards = _safe(row, "passing_yards")
            existing.passing_tds = _safe(row, "passing_tds")
            existing.interceptions = _safe(row, "interceptions")
            existing.sacks = _safe(row, "sacks")
            existing.sack_yards = _safe(row, "sack_yards")
            existing.passing_first_downs = _safe(row, "passing_first_downs")
            existing.sack_fumbles = _safe(row, "sack_fumbles")

            # Rushing
            existing.carries = _safe(row, "carries")
            existing.rushing_yards = _safe(row, "rushing_yards")
            existing.rushing_tds = _safe(row, "rushing_tds")
            existing.rushing_first_downs = _safe(row, "rushing_first_downs")
            existing.rushing_fumbles = _safe(row, "rushing_fumbles")

            # Receiving
            existing.receptions = _safe(row, "receptions")
            existing.targets = _safe(row, "targets")
            existing.receiving_yards = _safe(row, "receiving_yards")
            existing.receiving_tds = _safe(row, "receiving_tds")
            existing.receiving_fumbles = _safe(row, "receiving_fumbles")
            existing.receiving_first_downs = _safe(row, "receiving_first_downs")
            existing.receiving_yards_after_catch = _safe(row, "receiving_yards_after_catch")

            existing.updated_at = datetime.utcnow()
            count += 1

        # Flush offensive stats so subsequent loops can find existing records
        session.flush()

        # Write longest rush/reception from PBP
        for _, row in longest_plays.iterrows():
            pid = row.get("player_id")
            if not pid or (isinstance(pid, float) and pd.isna(pid)):
                continue
            season_val = int(row["season"])

            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=pid, season=season_val
            ).first()
            if not existing:
                continue

            if "longest_rush" in row and row["longest_rush"] > 0:
                existing.longest_rush = float(row["longest_rush"])
            if "longest_reception" in row and row["longest_reception"] > 0:
                existing.longest_reception = float(row["longest_reception"])

        session.flush()

        # Process defensive stats
        for _, row in defensive.iterrows():
            pid = row.get("player_id")
            if not pid or (isinstance(pid, float) and pd.isna(pid)):
                continue
            season_val = int(row["season"])

            player = session.get(Player, pid)
            if not player:
                continue

            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=pid, season=season_val
            ).first()
            if not existing:
                existing = PlayerSeasonStats(gsis_id=pid, season=season_val)
                session.add(existing)

            if "games_played" in row and row["games_played"] > 0:
                # Use max of existing and defensive games played
                existing.games_played = max(existing.games_played or 0, int(row["games_played"]))

            # Set team if not already set by offensive stats
            if not existing.team:
                existing.team = team_map.get((pid, season_val))

            existing.solo_tackles = _safe(row, "solo_tackles")
            existing.assists = _safe(row, "assists")
            existing.tackles = _safe(row, "tackles")
            existing.def_sacks = _safe(row, "def_sacks")
            existing.qb_hits = _safe(row, "qb_hits")
            existing.tackles_for_loss = _safe(row, "tackles_for_loss")
            existing.passes_defended = _safe(row, "passes_defended")
            existing.def_interceptions = _safe(row, "def_interceptions")
            existing.forced_fumbles = _safe(row, "forced_fumbles")
            existing.fumble_recoveries = _safe(row, "fumble_recoveries")
            existing.defensive_tds = _safe(row, "defensive_tds")

            existing.updated_at = datetime.utcnow()
            count += 1

        # Flush defensive stats before kicking loop
        session.flush()

        # Process kicking stats
        for _, row in kicking.iterrows():
            pid = row.get("player_id")
            if not pid or (isinstance(pid, float) and pd.isna(pid)):
                continue
            season_val = int(row["season"])

            player = session.get(Player, pid)
            if not player:
                continue

            existing = session.query(PlayerSeasonStats).filter_by(
                gsis_id=pid, season=season_val
            ).first()
            if not existing:
                existing = PlayerSeasonStats(gsis_id=pid, season=season_val)
                session.add(existing)

            if "games_played" in row and row["games_played"] > 0:
                existing.games_played = max(existing.games_played or 0, int(row["games_played"]))

            if not existing.team:
                existing.team = team_map.get((pid, season_val))

            existing.fg_made = _safe(row, "fg_made")
            existing.fg_attempts = _safe(row, "fg_attempts")
            existing.fg_made_40_49 = _safe(row, "fg_made_40_49")
            existing.fg_made_50_plus = _safe(row, "fg_made_50_plus")
            existing.long_fg = _safe(row, "long_fg")
            existing.xp_made = _safe(row, "xp_made")
            existing.xp_attempts = _safe(row, "xp_attempts")
            existing.kicking_points = _safe(row, "kicking_points")

            existing.updated_at = datetime.utcnow()
            count += 1

        session.commit()
        print(f"Ingested stats for {count} player-season entries.")
        for s in seasons:
            _log_ingestion(session, s, "nfl_data_py", count, "success", started_at=started)
        return count

    except Exception as e:
        session.rollback()
        print(f"Error ingesting stats: {e}")
        import traceback
        traceback.print_exc()
        for s in seasons:
            _log_ingestion(session, s, "nfl_data_py", 0, "error", str(e), started_at=started)
        raise
    finally:
        session.close()


def refresh_all(season: int):
    """Run full data refresh for a given season."""
    print(f"\n{'='*60}")
    print(f"  SSAT Rankings Data Refresh — Season {season}")
    print(f"{'='*60}\n")

    init_rankings_db()

    print("Step 1/2: Ingesting player roster...")
    ingest_players()

    print(f"\nStep 2/2: Ingesting all stats...")
    ingest_all_stats([season])

    print(f"\n{'='*60}")
    print(f"  Refresh complete for season {season}!")
    print(f"{'='*60}\n")


def refresh_all_seasons(start_year: int = 1999, end_year: int = 2025):
    """Ingest all seasons from start_year to end_year."""
    print(f"\n{'='*60}")
    print(f"  SSAT Rankings — Full Historical Ingestion ({start_year}–{end_year})")
    print(f"{'='*60}\n")

    init_rankings_db()

    print("Step 1: Ingesting player roster (one-time)...")
    ingest_players()

    total = end_year - start_year + 1
    for i, year in enumerate(range(start_year, end_year + 1), 1):
        print(f"\n[{i}/{total}] Season {year}...")
        try:
            ingest_all_stats([year])
        except Exception as e:
            print(f"  ERROR on {year}: {e}")
            continue

    print(f"\n{'='*60}")
    print(f"  Historical ingestion complete ({start_year}–{end_year})!")
    print(f"{'='*60}\n")


# --- Helper functions ---

def _safe(row, col, default=0.0):
    """Safely extract a float from a pandas row."""
    val = row.get(col, default)
    if pd.isna(val):
        return default
    return float(val)
