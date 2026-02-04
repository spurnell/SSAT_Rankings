# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Server Management (IMPORTANT)

**The app runs on these ports during development:**
- Frontend: `localhost:3000`
- Backend: `localhost:8000`

**You have permission to:**
- Kill processes on ports 3000 and 8000 as needed
- Restart servers without asking
- Use `lsof -ti:3000,3001 | xargs kill -9` to clear port conflicts

**Always ensure the frontend runs on port 3000** - if Next.js tries to use 3001, kill the conflicting process first.

## Project Overview

NFL Player Rankings website using z-score methodology to evaluate players across multiple statistical categories. Supports defensive players (DEF), quarterbacks (QB), running backs (RB), wide receivers (WR), tight ends (TE), and kickers (K).

## Architecture

- **Frontend**: Next.js 14 with App Router, TypeScript, Tailwind CSS, Recharts
- **Backend**: Python FastAPI with Pydantic models, SQLAlchemy, SQLite
- **Data Source**: nfl-data-py library (regular season weeks 1-18 only)
- **Blog Generation**: Claude API via Anthropic SDK for AI-generated content

## Development Commands

### Backend
```bash
cd backend
source venv/bin/activate  # Must activate venv first
uvicorn app.main:app --reload  # Runs on port 8000
```

### Frontend
```bash
cd frontend
npm run dev    # Development server on port 3000
npm run build  # Production build
npm run lint   # ESLint
```

### Blog CLI
```bash
cd backend && source venv/bin/activate
python -m app.cli.generate_blog insights                          # View available insights
python -m app.cli.generate_blog generate power-rankings --group RB # Power rankings for position group (DEF, QB, RB, WR, TE, K)
python -m app.cli.generate_blog generate power-rankings --preview # Preview without saving
python -m app.cli.generate_blog generate spotlight --player "Micah Parsons"
python -m app.cli.generate_blog generate comparison --player1 "T.J. Watt" --player2 "Myles Garrett"
python -m app.cli.generate_blog list --drafts                     # List all posts
python -m app.cli.generate_blog publish <slug>                    # Publish a draft
```

### Blog Content Guidelines
- **Power rankings posts MUST include category scores** under each player's name (e.g., "Efficiency: 87.0 | Volume: 97.3 | Scoring: 85.1 | Receiving: 92.8")
- Don't hype up 100 scores - they're a natural result of the ranking system, not unprecedented achievements

## Environment Variables

Backend (`.env` in `backend/`):
- `ANTHROPIC_API_KEY` - Required for blog generation
- `DATABASE_URL` - SQLite path (default: `sqlite:///./data/rankings.db`)

Frontend:
- `NEXT_PUBLIC_API_URL` - Backend URL (default: `http://localhost:8000`)

## Key Architecture Concepts

### Position Configuration (`backend/app/core/position_config.py`)
Single source of truth for all position groups. Defines:
- Categories and their stats (e.g., DEF has run_defense, pass_rush, coverage, playmaking)
- Weights for each category
- Which stats use log scaling (rare events like TDs, interceptions)

### Z-Score Ranking Engine (`backend/app/core/ranking.py`)
- Calculates z-scores for each stat within position groups
- Applies log scaling for rare event stats to prevent outlier dominance
- Clamps z-scores to [-3, +3] standard deviations
- Final scores: 80 = average, range 60-100
- **There will ALWAYS be a player with a score of 100** - this is how the rescaling works (min-max normalization to 60-100 range). Don't treat 100 as surprising or unprecedented in blog content.

### Data Flow
1. `nfl_data.py` fetches play-by-play data → aggregates to player stats
2. `ranking.py` computes z-scores and category scores per position group
3. `rankings.py` API routes expose `/api/rankings/{position_group}`
4. Frontend fetches via `lib/api.ts` → displays in `RankingsTable.tsx`

### Player Profile Panel
- `PlayerProfilePanel.tsx` - Container with close button
- `RadarChart.tsx` - Category comparison visualization (supports 2-player compare)
- `ProfileStatsTable.tsx` - Detailed stats with percentile rankings
