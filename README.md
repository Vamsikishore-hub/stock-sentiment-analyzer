# Stock Market Sentiment Analyzer

A real-time stock market intelligence system that tracks 10 major tech stocks, runs NLP sentiment analysis on financial news using FinBERT, and generates macro reasoning using a locally hosted Llama 3.2 model — no paid AI APIs required.

[Dashboard](http://localhost:3000) | [API Docs](http://localhost:8000/docs)

---

## Prerequisites

Before you begin, make sure you have the following installed on your machine:
- **Git**
- **Docker Desktop**
- **NewsAPI Key** — free at [newsapi.org](https://newsapi.org)
- **Alpha Vantage Key** — free at [alphavantage.co/support/#api-key](https://www.alphavantage.co/support/#api-key)

---

## Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Vamsikishore-hub/stock-sentiment-analyzer.git
   ```

2. **Navigate to the Project Directory**:
   ```bash
   cd stock-sentiment-analyzer
   ```

3. **Configure Environment**:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and add your keys:
   ```env
   NEWSAPI_KEY=your_newsapi_key_here
   ALPHA_VANTAGE_KEY=your_alpha_vantage_key_here
   ```

4. **Build and Start**:
   ```bash
   docker-compose up --build
   ```
   > **First build takes 10–15 minutes** — downloads FinBERT (~500 MB) and Llama 3.2 (~2 GB). Subsequent starts are much faster.

5. **Wait for the Ready Banner**:

   When everything is loaded you will see this in the terminal:
   ```
   ╔═══════════════════════════════════════════════════════╗
   ║      ✅  SMSA IS READY — ALL SYSTEMS ACTIVE           ║
   ║      🌐  http://localhost:3000                        ║
   ║      You are good to use the website! 🚀              ║
   ╚═══════════════════════════════════════════════════════╝
   ```

6. **Access the Application**:
   - Dashboard: [http://localhost:3000](http://localhost:3000)
   - API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## How It Works

1. Every 15 minutes the pipeline fetches live prices, news headlines, and Reddit posts
2. **FinBERT** scores every headline as bullish, neutral, or bearish
3. Scores are aggregated per stock into a sentiment score from -1.0 to +1.0
4. **Llama 3.2** (running locally via Ollama) analyzes the headlines and generates macro reasoning — e.g. *"TSLA bearish due to declining EV demand and increasing competition"*
5. Dashboard shows Buy / Sell / Hold signals, price + sentiment charts, trending stocks, and a live news feed

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard` | Full dashboard payload — stocks, news, macro |
| GET | `/api/stocks/` | All 10 stocks with latest sentiment and price |
| GET | `/api/stocks/{symbol}` | Stock detail with price history and recent news |
| GET | `/api/stocks/trending` | Stocks ranked by mention volume |
| GET | `/api/news/` | News feed (optional `?symbol=TSLA` to filter) |
| GET | `/api/sentiment/` | Latest sentiment records per stock |
| POST | `/api/sentiment/refresh` | Manually trigger a full analysis run |
| GET | `/api/macro/latest` | Latest Llama macro summary and events |
| GET | `/health` | Health check |

---

## Sentiment Score Interpretation

| Score Range | Label | Signal |
|---|---|---|
| +0.25 to +1.0 | 🟢 Bullish | **Buy** |
| +0.15 to +0.24 | 🟢 Bullish | Hold |
| -0.14 to +0.14 | 🟡 Neutral | **Hold** |
| -0.15 to -0.24 | 🔴 Bearish | Hold |
| -0.25 to -1.0 | 🔴 Bearish | **Sell** |

---

## Troubleshooting

1. **Dashboard shows $0.00 prices**:
   - Alpha Vantage has a 25 requests/day free limit — prices will show after the next refresh cycle
   - Check your `ALPHA_VANTAGE_KEY` in `.env`

2. **Macro panel is empty**:
   - Llama 3.2 takes 2–3 minutes to load on first startup — wait for the ready banner
   - Run `docker-compose logs backend --tail=30` to check progress

3. **"dependency failed to start: backend is unhealthy"**:
   - This happens if you stop the containers before Llama finishes loading
   - Just run `docker-compose up` again and wait for the banner

4. **Port already in use**:
   ```bash
   docker-compose down
   docker-compose up --build
   ```

5. **Want a clean restart**:
   ```bash
   docker-compose down -v
   docker-compose up --build
   ```
   > `-v` removes the database volume — all stored data will be cleared

---

## Project Structure

- **Backend**:
  - `backend/app/main.py` — FastAPI app with lifespan and all routers
  - `backend/app/services/price_service.py` — Alpha Vantage + Yahoo Finance fallback
  - `backend/app/services/news_service.py` — NewsAPI + Reddit with smart financial filter
  - `backend/app/services/finbert_service.py` — FinBERT inference and score aggregation
  - `backend/app/services/gpt_service.py` — Llama 3.2 via Ollama for macro reasoning
  - `backend/app/services/analysis_service.py` — Master pipeline orchestrator
  - `backend/app/services/scheduler.py` — APScheduler background jobs and startup sequence
  - `backend/app/models/models.py` — SQLAlchemy ORM models
  - `backend/requirements.txt` — Python dependencies
  - `backend/Dockerfile` — Backend container
- **Frontend**:
  - `frontend/src/pages/Dashboard.jsx` — Main dashboard page
  - `frontend/src/components/cards/StockCard.jsx` — Per-stock sentiment card
  - `frontend/src/components/charts/StockChart.jsx` — Price + sentiment Recharts chart
  - `frontend/src/components/panels/NewsFeed.jsx` — Filterable news feed
  - `frontend/src/components/panels/MacroPanel.jsx` — Llama macro analysis panel
  - `frontend/src/components/panels/TrendingTable.jsx` — Stocks by mention volume
  - `frontend/src/hooks/useDashboard.js` — Polling hook with 60s auto-refresh
  - `frontend/Dockerfile` — Multi-stage React build → nginx
- **Other**:
  - `docker-compose.yml` — 5-service orchestration (db, ollama, ollama-init, backend, frontend)
  - `.env.example` — Environment variable template
  - `setup.py` — Package metadata
  - `README.md` — Project documentation

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite, Recharts |
| Backend | FastAPI, Python 3.11 |
| Database | PostgreSQL 16 |
| Sentiment NLP | FinBERT (`ProsusAI/finbert`) — HuggingFace Transformers |
| Macro Reasoning | Llama 3.2 3B via Ollama — runs fully locally |
| Price Data | Alpha Vantage API + Yahoo Finance fallback |
| News Data | NewsAPI |
| Deployment | Docker, Docker Compose |

---

## Affiliation

Built by **Vamsi Kishore Nallagopu**
Degree: M.S. Computer Science
Institution: California State University, San Bernardino
[GitHub](https://github.com/Vamsikishore-hub) | [LinkedIn](https://www.linkedin.com/in/vamsi-kishore-nallagopu-097707240/)
