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

NFL Player Rankings website using z-score methodology to evaluate players across multiple statistical categories. Supports defensive players (DEF), quarterbacks (QB), running backs (RB), wide receivers (WR), tight ends (TE), and kickers (K). Features include:

- **Season & Career Rankings** — current season and historical career leaderboards
- **Custom Rankings** — users upload their own data (CSV/XLSX), configure categories, compute z-score rankings, and share results via public links
- **Blog** — AI-generated content (power rankings, player spotlights, comparisons) via Claude API
- **Authentication** — Clerk-based auth for custom rankings dashboard (optional, degrades gracefully)

## Architecture

- **Frontend**: Next.js 14 with App Router, TypeScript, Tailwind CSS, Recharts
- **Backend**: Python FastAPI with Pydantic models, SQLAlchemy, SQLite
- **Auth**: Clerk (frontend provider + backend JWT validation via JWKS)
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

Backend (`backend/.env`):
- `ANTHROPIC_API_KEY` — Required for blog generation
- `DATABASE_URL` — SQLite path (default: `sqlite:///./data/rankings.db`)
- `CLERK_ISSUER` — Clerk issuer URL for JWT validation (optional, needed for custom rankings auth)

Frontend (`frontend/.env.local`):
- `NEXT_PUBLIC_API_URL` — Backend URL (default: `http://localhost:8000`)
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` — Clerk publishable key (optional; if unset, auth UI is hidden and app works without login)

Backend config (`backend/app/core/config.py`):
- `current_season` — Controls which NFL season data is fetched (currently `2025`)

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
- Used by both NFL rankings and custom rankings systems

### Data Flow

**NFL Season Rankings:**
1. `nfl_data.py` fetches play-by-play data → aggregates to player stats
2. `ranking.py` computes z-scores and category scores per position group
3. `rankings.py` API routes expose `/api/rankings/{position_group}`
4. Frontend fetches via `lib/api.ts` → displays in `RankingsTable.tsx`

**Career Rankings:**
1. `career_data.py` fetches historical data → cumulative totals or per-game averages
2. Same z-score engine computes rankings across careers
3. `/api/career-rankings/{position_group}` exposes results (modes: `cumulative`, `per_game`)
4. Frontend `/rankings` page has Season/Career toggle

**Custom Rankings:**
1. User uploads CSV/XLSX → `file_parser.py` validates and parses (min 10 rows, 2+ numeric columns)
2. Stored as `CustomDataset` in database
3. User configures categories via `CategoryConfigurator.tsx` (stats, weights, higher/lower-is-better)
4. `custom_ranking_service.py` computes z-scores → normalize to 60-100 → weighted overall scores
5. Results cached in `RankingConfig.results`
6. Optional sharing via generated slug → public view at `/shared/{slug}`

### Player Profile Panel
- `PlayerProfilePanel.tsx` — Container with close button
- `RadarChart.tsx` — Category comparison visualization (supports 2-player compare)
- `ProfileStatsTable.tsx` — Detailed stats with percentile rankings

### Authentication
- **Frontend**: `ClerkProviderWrapper.tsx` wraps app with ClerkProvider if publishable key is set. `useOptionalAuth()` hook provides `getToken()` for API calls.
- **Backend**: `app/core/auth.py` has `get_current_user()` FastAPI dependency — decodes JWT, fetches Clerk JWKS, verifies RS256 signature, returns `clerk_user_id`.
- **Graceful degradation**: If Clerk keys are not configured, auth UI is hidden and custom rankings features are inaccessible. NFL rankings, blog, and shared links work without auth.

## Frontend Routes

| Route | Auth Required | Description |
|-------|--------------|-------------|
| `/` | No | Home/landing page |
| `/about` | No | Methodology explanation |
| `/rankings` | No | NFL season & career rankings (with mode toggle) |
| `/rankings/custom` | No | NFL rankings with custom category weights |
| `/blog` | No | Blog listing |
| `/blog/[slug]` | No | Individual blog post |
| `/shared/[slug]` | No | Public shared custom ranking view |
| `/dashboard` | Yes | Custom rankings dashboard (datasets & rankings) |
| `/dashboard/upload` | Yes | Upload CSV/XLSX for custom rankings |
| `/dashboard/configure/[datasetId]` | Yes | Configure ranking categories |
| `/dashboard/results/[rankingId]` | Yes | View custom ranking results + share |
| `/sign-in/[[...sign-in]]` | — | Clerk sign-in |
| `/sign-up/[[...sign-up]]` | — | Clerk sign-up |

## Backend API Endpoints

### Rankings (Public)
- `GET /api/position-groups` — All position groups with categories
- `GET /api/position-config/{position_group}` — Position config with category weights
- `GET /api/rankings/{position_group}` — Season rankings (params: `position`, `min_games`)
- `GET /api/career-rankings/{position_group}` — Career leaderboards (params: `mode`, `min_seasons`, `min_games`)
- `GET /api/players/{player_id}` — Individual player details (params: `position_group`)
- `GET /api/compare` — Compare players (params: `ids`, `position_group`)
- `POST /api/calculate` — Rankings with custom weights (params: `position_group`, `weights`, `mode`, `min_games`, `min_seasons`)

### Blog (Public)
- `GET /api/blog/posts` — List published posts (params: `limit`, `offset`, `post_type`)
- `GET /api/blog/posts/{slug}` — Individual blog post

### Custom Rankings (Auth Required)
- `POST /api/custom/datasets` — Upload file (multipart: `file`, `title`, `name_column`)
- `GET /api/custom/datasets` — List user's datasets
- `GET /api/custom/datasets/{dataset_id}` — Get dataset with data
- `DELETE /api/custom/datasets/{dataset_id}` — Delete dataset
- `POST /api/custom/datasets/{dataset_id}/rankings` — Create ranking config (body: `title`, `categories`)
- `GET /api/custom/rankings` — List user's rankings
- `GET /api/custom/rankings/{ranking_id}` — Get ranking with results
- `PUT /api/custom/rankings/{ranking_id}` — Update and recompute ranking
- `DELETE /api/custom/rankings/{ranking_id}` — Delete ranking
- `POST /api/custom/rankings/{ranking_id}/share` — Generate share link
- `DELETE /api/custom/rankings/{ranking_id}/share` — Revoke sharing

### Shared (Public)
- `GET /api/shared/{slug}` — View shared ranking (no auth)

## Deployment

- **Backend**: Deployed on Render.com (see `backend/render.yaml`). Uses `uvicorn app.main:app --host 0.0.0.0 --port $PORT`.
- **Frontend**: Next.js deployment. Redirects configured in `frontend/next.config.mjs`:
  - `/career` → `/rankings`
  - `/how-it-works` → `/about`
  - `/custom` → `/dashboard`
  - `/custom/:path*` → `/dashboard/:path*`
- **Production domain**: `sportssatrankings.com` (listed in CORS origins)

## Database Models

All models use SQLAlchemy with SQLite (`backend/data/blog.db`).

**BlogPost** (`app/db/models.py`):
- `id`, `slug` (unique), `title`, `excerpt`, `content`, `post_type`, `featured_players` (JSON), `tags` (JSON), `published_at`, `created_at`, `is_published`

**CustomDataset** (`app/db/custom_models.py`):
- `id`, `clerk_user_id` (indexed), `title`, `original_filename`, `row_count`, `column_names` (JSON), `data` (JSON), `name_column`, `created_at`, `updated_at`
- Has many `ranking_configs` (cascade delete)

**RankingConfig** (`app/db/custom_models.py`):
- `id`, `dataset_id` (FK), `clerk_user_id` (indexed), `title`, `categories` (JSON), `results` (JSON — cached computed rankings), `results_computed_at`, `share_slug` (unique), `is_shared`, `created_at`, `updated_at`
- Belongs to `CustomDataset`

## Dark Mode

`globals.css` uses CSS variables (`--background`, `--foreground`) with `@media (prefers-color-scheme: dark)`. When styling form inputs and selects, always use explicit `text-slate-900` with `bg-white` to ensure readability in both light and dark modes — otherwise inputs inherit the dark foreground color and become invisible against white backgrounds.
