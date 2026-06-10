from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import warnings

# ── Suppress noisy third-party warnings ───────────────────────
warnings.filterwarnings("ignore", category=FutureWarning)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("yfinance").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# ── Clean logging format ───────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

from app.api import stocks, news, sentiment, macro
from app.core.database import engine, Base
from app.services.scheduler import start_scheduler, stop_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("━" * 55)
    logger.info("  SMSA  Stock Market Sentiment Analyzer — Starting")
    logger.info("━" * 55)
    async with engine.begin() as conn:
        await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))
    logger.info("  [1/3]  Database connected ✓")
    await start_scheduler()
    yield
    await stop_scheduler()
    await engine.dispose()
    logger.info("  Shutdown complete.")


app = FastAPI(
    title="Stock Market Sentiment Analyzer",
    version="1.0.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(stocks.router,    prefix="/api/stocks",    tags=["Stocks"])
app.include_router(news.router,      prefix="/api/news",      tags=["News"])
app.include_router(sentiment.router, prefix="/api/sentiment", tags=["Sentiment"])
app.include_router(macro.router,     prefix="/api/macro",     tags=["Macro"])


@app.get("/health")
async def health():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/dashboard")
async def dashboard_data():
    from app.core.database import AsyncSessionLocal
    from app.services.price_service import get_latest_prices
    from app.services.news_service import get_recent_articles
    from sqlalchemy import select, desc
    from app.models.models import StockSentiment, MacroEvent
    from app.core.config import settings

    async with AsyncSessionLocal() as db:
        prices = await get_latest_prices(db)
        price_map = {
            p.symbol: {
                "price": p.price, "change": p.change,
                "change_pct": p.change_pct, "volume": p.volume
            }
            for p in prices
        }

        stock_scores = {}
        for sym in settings.tracked_stocks:
            stmt = (
                select(StockSentiment)
                .where(StockSentiment.symbol == sym)
                .order_by(desc(StockSentiment.computed_at))
                .limit(1)
            )
            row = await db.execute(stmt)
            s = row.scalar_one_or_none()
            if s:
                stock_scores[sym] = {
                    "label": s.sentiment_label,
                    "score": s.sentiment_score,
                    "signal": s.signal,
                    "article_count": s.article_count,
                    "mention_count": s.mention_count,
                    "gpt_reasoning": s.gpt_reasoning,
                }

        stmt = select(MacroEvent).order_by(desc(MacroEvent.computed_at)).limit(1)
        latest_macro = (await db.execute(stmt)).scalar_one_or_none()

        stmt2 = select(MacroEvent).order_by(desc(MacroEvent.computed_at)).limit(5)
        macro_events_rows = (await db.execute(stmt2)).scalars().all()

        articles = await get_recent_articles(db, limit=30)

        stocks_out = []
        for sym in settings.tracked_stocks:
            pd = price_map.get(sym, {})
            ss = stock_scores.get(sym, {})
            stocks_out.append({
                "symbol": sym,
                "price": pd.get("price", 0),
                "change": pd.get("change", 0),
                "change_pct": pd.get("change_pct", 0),
                "volume": pd.get("volume", 0),
                "sentiment_label": ss.get("label", "neutral"),
                "sentiment_score": ss.get("score", 0),
                "signal": ss.get("signal", "Hold"),
                "gpt_reasoning": ss.get("gpt_reasoning"),
                "article_count": ss.get("article_count", 0),
                "mention_count": ss.get("mention_count", 0),
            })

        return {
            "stocks": stocks_out,
            "trending": sorted(stocks_out, key=lambda x: x["mention_count"], reverse=True)[:5],
            "news_feed": [
                {
                    "id": a.id,
                    "title": a.title,
                    "source": a.source,
                    "url": a.url,
                    "published_at": a.published_at.isoformat() if a.published_at else None,
                    "related_symbols": a.related_symbols,
                    "sentiment_label": a.sentiment_label,
                    "sentiment_score": a.sentiment_score,
                    "is_reddit": a.is_reddit,
                }
                for a in articles
            ],
            "macro_summary": latest_macro.gpt_analysis if latest_macro else None,
            "macro_events": [
                {
                    "event_type": e.event_type,
                    "summary": e.summary,
                    "impact": e.impact,
                    "affected_symbols": e.affected_symbols,
                    "computed_at": e.computed_at.isoformat(),
                }
                for e in macro_events_rows
            ],
            "last_updated": prices[0].fetched_at.isoformat() if prices else None,
        }
