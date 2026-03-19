# SSAT Rankings

NFL Defensive Player Rankings using Z-Score Methodology

## Project Structure

```
SSAT_Rankings/
├── frontend/          # Next.js 14 application
├── backend/           # Python FastAPI application
├── README.md
└── CLAUDE.md
```

## Getting Started

### Backend Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API will be available at http://localhost:8000

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend will be available at http://localhost:3000

## API Endpoints

- `GET /health` - Health check
- `GET /api/rankings` - Get player rankings with optional filters
- `GET /api/players/{id}` - Get player details
- `GET /api/compare?ids=1,2,3` - Compare multiple players
- `POST /api/calculate` - Calculate rankings with custom weights

## Ranking Methodology

Players are ranked using a z-score based system across four categories:

1. **Run Defense** - Tackles, solo tackles, assists, tackles for loss
2. **Pass Rush** - Sacks, QB hits, tackles for loss
3. **Coverage** - Passes defended, interceptions
4. **Playmaking** - Forced fumbles, fumble recoveries, interceptions, defensive TDs

Scores are normalized to a 60-100 scale where 80 represents average.

## Tech Stack

- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Backend**: Python 3.10+, FastAPI, Pydantic
- **Data**: nflreadpy for NFL statistics (nflverse data)
