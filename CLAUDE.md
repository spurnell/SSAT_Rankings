# SSAT Rankings - Claude Code Context

## Project Overview
NFL Defensive Player Rankings website using z-score methodology to evaluate players across multiple statistical categories.

## Architecture
- **Frontend**: Next.js 14 with App Router, TypeScript, Tailwind CSS
- **Backend**: Python FastAPI with Pydantic models
- **Data Source**: nfl-data-py library (with fallback sample data)

## Key Files

### Backend
- `backend/app/main.py` - FastAPI entry point with CORS and routes
- `backend/app/core/ranking.py` - Z-score calculation engine
- `backend/app/services/nfl_data.py` - NFL data fetching and processing
- `backend/app/api/routes/rankings.py` - API endpoints
- `backend/app/models/schemas.py` - Pydantic models

### Frontend
- `frontend/src/app/layout.tsx` - Root layout with Navbar
- `frontend/src/app/rankings/page.tsx` - Rankings page
- `frontend/src/components/RankingsTable.tsx` - Main rankings display
- `frontend/src/lib/api.ts` - API client utilities

## Running the Project

### Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm run dev
```

## Ranking Categories
1. Run Defense: tackles, solo_tackles, assists, tackles_for_loss
2. Pass Rush: sacks, qb_hits, tackles_for_loss
3. Coverage: passes_defended, interceptions
4. Playmaking: forced_fumbles, fumble_recoveries, interceptions, defensive_tds

## Score Scale
- Scores range from 60-100
- 80 = average performance
- Z-scores clamped to [-3, +3] standard deviations
