// Stat display names for all position groups (standard + PFF)
export const STAT_LABELS: Record<string, string> = {
  // Defensive (standard)
  tackles: "Tackles",
  solo_tackles: "Solo Tackles",
  assists: "Assists",
  sacks: "Sacks",
  qb_hits: "QB Hits",
  tackles_for_loss: "TFL",
  passes_defended: "Passes Defended",
  interceptions: "Interceptions",
  forced_fumbles: "Forced Fumbles",
  fumble_recoveries: "Fumble Recoveries",
  defensive_tds: "Defensive TDs",

  // QB (standard)
  pass_attempts: "Pass Attempts",
  completions: "Completions",
  completion_pct: "Completion %",
  pass_yards: "Pass Yards",
  pass_tds: "Pass TDs",
  passer_rating: "Passer Rating",
  yards_per_attempt: "Yards/Attempt",
  first_downs: "First Downs",
  int_rate_inv: "INT Rate (low = good)",
  sack_rate_inv: "Sack Rate (low = good)",
  fumbles_inv: "Fumbles (low = good)",

  // RB (standard)
  rush_attempts: "Rush Attempts",
  rush_yards: "Rush Yards",
  yards_per_carry: "Yards/Carry",
  rush_tds: "Rush TDs",
  longest_rush: "Longest Rush",
  fumbles: "Fumbles",
  receptions: "Receptions",
  rec_yards: "Rec Yards",
  rec_tds: "Rec TDs",
  targets: "Targets",
  touches: "Touches",
  yards_per_touch: "Yards/Touch",
  total_tds: "Total TDs",
  success_rate: "Success Rate",

  // WR/TE (standard)
  catch_rate: "Catch Rate",
  yards_per_reception: "Yards/Rec",
  yards_per_target: "Yards/Target",
  longest_rec: "Longest Rec",
  yards_after_catch: "YAC",

  // Kicker (standard)
  fg_made: "FG Made",
  fg_attempts: "FG Attempts",
  fg_pct: "FG %",
  fg_made_40_49: "FG 40-49",
  fg_made_50_plus: "FG 50+",
  long_fg: "Long FG",
  xp_made: "XP Made",
  xp_attempts: "XP Attempts",
  xp_pct: "XP %",
  total_points: "Total Points",

  // PFF QB
  accuracy_percent: "Accuracy %",
  big_time_throws: "Big Time Throws",
  drop_rate_inv: "Drop Rate (low = good)",
  twp_rate_inv: "Turnover-Worthy Plays (low = good)",
  thrown_aways: "Thrown Aways",
  interceptions_inv: "Interceptions (low = good)",
  pressure_to_sack_rate_inv: "Pressure→Sack Rate (low = good)",
  sack_percent_inv: "Sack % (low = good)",
  scrambles: "Scrambles",
  hit_as_threw: "Hit As Threw",
  ypa: "Yards Per Attempt",
  touchdowns: "Touchdowns",

  // PFF RB
  yco_attempt: "Yards After Contact / Attempt",
  elusive_rating: "Elusive Rating",
  breakaway_percent: "Breakaway %",
  explosive: "Explosive Runs",
  longest: "Longest Play",
  yards: "Yards",
  avoided_tackles: "Avoided Tackles",
  yprr: "Yards Per Route Run",

  // PFF WR/TE
  grades_pass_route: "PFF Route Grade",
  route_rate: "Route Rate",
  caught_percent: "Catch %",
  contested_catch_rate: "Contested Catch %",
  yards_after_catch_per_reception: "YAC / Reception",
  targeted_qb_rating: "Targeted QB Rating",
  avg_depth_of_target: "Avg Depth of Target",

  // PFF TE blocking
  grades_pass_block: "PFF Pass Block Grade",
  pass_block_percent: "Pass Block %",
  pressures_allowed_inv: "Pressures Allowed (low = good)",

  // PFF DEF Front 7
  grades_pass_rush_defense: "PFF Pass Rush Grade",
  pass_rush_win_rate: "Pass Rush Win %",
  total_pressures: "Total Pressures",
  prp: "Pass Rush Productivity",
  grades_run_defense: "PFF Run Defense Grade",
  stop_percent: "Stop %",
  missed_tackle_rate_inv: "Missed Tackle Rate (low = good)",
  grades_tackle: "PFF Tackle Grade",
  stops: "Stops",
  pass_break_ups: "Pass Break-Ups",

  // PFF DEF Secondary
  grades_coverage_defense: "PFF Coverage Grade",
  forced_incompletion_rate: "Forced Incompletion %",
  coverage_snaps_per_target: "Coverage Snaps / Target",
  qb_rating_against_inv: "QB Rating Against (low = good)",
  catch_rate_inv: "Catch Rate Allowed (low = good)",
  coverage_snaps_per_reception: "Coverage Snaps / Reception",
  yards_per_coverage_snap_inv: "Yards / Coverage Snap (low = good)",

  // PFF Kicker
  total_percent: "FG % (Total)",
  pat_percent: "PAT %",
  grades_fgep_kicker: "PFF FG/PAT Grade",
  fifty_percent: "FG % (50+)",
  forty_percent: "FG % (40-49)",
  fifty_made: "FG Made (50+)",
  total_made: "FG Made (Total)",
  pat_made: "PAT Made",
  grades_kickoff_kicker: "PFF Kickoff Grade",
  touchbacks: "Touchbacks",
  average_yards_per_return_inv: "Yards/Return Allowed (low = good)",
};

// Stats to hide from the player profile stat table (internal calculations)
export const HIDDEN_STATS = new Set([
  "int_rate_inv",
  "sack_rate_inv",
  "fumbles_inv",
  "games_played",
]);

export function getStatLabel(key: string): string {
  return (
    STAT_LABELS[key] ||
    key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())
  );
}
