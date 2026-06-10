import logging
from typing import List, Dict, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.config import settings
from app.models.models import NewsArticle, StockSentiment, MacroEvent, StockPrice
from app.services.finbert_service import (
    analyze_headlines,
    aggregate_sentiment,
    score_to_signal,
)
from app.services.gpt_service import get_macro_analysis
from app.services.news_service import get_recent_articles, save_articles, fetch_all_news
from app.services.price_service import fetch_prices, save_prices

logger = logging.getLogger(__name__)


def _coerce_symbols(value) -> Optional[str]:
    """Ensure affected_symbols is always a comma-separated string, never a list."""
    if value is None:
        return None
    if isinstance(value, list):
        return ",".join(str(v) for v in value)
    return str(value)


def _coerce_str(value, max_len: int = None) -> Optional[str]:
    """Ensure a value is a string, optionally truncated."""
    if value is None:
        return None
    s = str(value)
    if max_len and len(s) > max_len:
        s = s[:max_len]
    return s


async def run_full_analysis(db: AsyncSession, verbose: bool = False) -> Dict:
    logger.info("Starting full analysis pipeline...")

    # ── 1. Prices ─────────────────────────────────────────
    prices = await fetch_prices(settings.tracked_stocks)
    await save_prices(db, prices)
    price_map = {p["symbol"]: p for p in prices}
    logger.info(f"Fetched prices for {len(prices)} stocks")

    # ── 2. News ───────────────────────────────────────────
    articles = await fetch_all_news()
    saved_count = await save_articles(db, articles)
    logger.info(f"Saved {saved_count} new articles")

    # ── 3. FinBERT ────────────────────────────────────────
    recent = await get_recent_articles(db, limit=200)
    unscored = [a for a in recent if a.sentiment_score is None]
    if unscored:
        texts = [f"{a.title}. {a.description or ''}" for a in unscored]
        sentiments = await analyze_headlines(texts)
        for article, (label, score) in zip(unscored, sentiments):
            article.sentiment_label = label
            article.sentiment_score = score
        await db.commit()
        logger.info(f"Scored {len(unscored)} articles with FinBERT")

    recent = await get_recent_articles(db, limit=200)

    # ── 4. Aggregate per-stock ────────────────────────────
    per_stock: Dict[str, List[float]] = {s: [] for s in settings.tracked_stocks}
    mention_counts: Dict[str, int] = {s: 0 for s in settings.tracked_stocks}

    for article in recent:
        if article.related_symbols and article.sentiment_score is not None:
            for sym in article.related_symbols.split(","):
                sym = sym.strip()
                if sym in per_stock:
                    per_stock[sym].append(article.sentiment_score)
                    mention_counts[sym] += 1

    stock_scores = {}
    for sym in settings.tracked_stocks:
        label, score = aggregate_sentiment(per_stock[sym])
        stock_scores[sym] = {
            "label": label,
            "score": score,
            "signal": score_to_signal(label, score),
            "article_count": len(per_stock[sym]),
            "mention_count": mention_counts[sym],
        }

    # ── 5. Llama Macro Reasoning ──────────────────────────
    all_headlines = [a.title for a in recent if a.title]
    score_map = {sym: stock_scores[sym]["score"] for sym in settings.tracked_stocks}
    gpt_result = await get_macro_analysis(all_headlines, score_map, settings.tracked_stocks)
    logger.info("GPT macro analysis complete")

    # ── 6. Save sentiments ────────────────────────────────
    for sym in settings.tracked_stocks:
        ss = stock_scores[sym]
        reasoning = None
        if gpt_result and "stock_reasoning" in gpt_result:
            reasoning = gpt_result["stock_reasoning"].get(sym)

        record = StockSentiment(
            symbol=sym,
            sentiment_label=ss["label"],
            sentiment_score=ss["score"],
            signal=ss["signal"],
            finbert_score=ss["score"],
            gpt_reasoning=_coerce_str(reasoning),
            article_count=ss["article_count"],
            mention_count=ss["mention_count"],
        )
        db.add(record)

    # ── 7. Save macro events (with type coercion) ─────────
    macro_summary = ""
    if gpt_result:
        macro_summary = _coerce_str(gpt_result.get("macro_summary", "")) or ""

        for evt in gpt_result.get("macro_events", []):
            record = MacroEvent(
                event_type=_coerce_str(evt.get("event_type"), max_len=200),
                summary=_coerce_str(evt.get("summary")) or "",
                gpt_analysis=macro_summary,
                affected_symbols=_coerce_symbols(evt.get("affected_symbols")),
                impact=_coerce_str(evt.get("impact"), max_len=20),
            )
            db.add(record)

    await db.commit()
    logger.info("Analysis pipeline complete")

    return _build_dashboard(price_map, stock_scores, gpt_result, recent)


def _build_dashboard(price_map, stock_scores, gpt_result, articles):
    stocks = []
    for sym in settings.tracked_stocks:
        pd = price_map.get(sym, {})
        ss = stock_scores.get(sym, {})
        reasoning = None
        if gpt_result and "stock_reasoning" in gpt_result:
            reasoning = gpt_result["stock_reasoning"].get(sym)

        stocks.append({
            "symbol": sym,
            "price": pd.get("price", 0),
            "change": pd.get("change", 0),
            "change_pct": pd.get("change_pct", 0),
            "volume": pd.get("volume", 0),
            "sentiment_label": ss.get("label", "neutral"),
            "sentiment_score": ss.get("score", 0),
            "signal": ss.get("signal", "Hold"),
            "gpt_reasoning": reasoning,
            "article_count": ss.get("article_count", 0),
            "mention_count": ss.get("mention_count", 0),
        })

    news_feed = [
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
        for a in articles[:30]
    ]

    macro_summary = gpt_result.get("macro_summary") if gpt_result else None
    macro_events = []
    if gpt_result:
        for evt in gpt_result.get("macro_events", []):
            macro_events.append({
                "event_type": _coerce_str(evt.get("event_type")),
                "summary": _coerce_str(evt.get("summary")),
                "impact": _coerce_str(evt.get("impact")),
                "affected_symbols": _coerce_symbols(evt.get("affected_symbols")),
            })

    trending = sorted(stocks, key=lambda x: x["mention_count"], reverse=True)

    return {
        "stocks": stocks,
        "trending": trending[:5],
        "news_feed": news_feed,
        "macro_summary": macro_summary,
        "macro_events": macro_events,
        "last_updated": datetime.utcnow().isoformat(),
    }
