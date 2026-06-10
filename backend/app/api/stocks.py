from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.core.database import get_db
from app.core.config import settings
from app.models.models import StockSentiment, StockPrice, NewsArticle
from app.schemas.schemas import (
    DashboardStockSchema,
    StockDetailSchema,
    PriceHistoryPoint,
    TrendingStockSchema,
)
from app.services.price_service import get_latest_prices, get_price_history
from app.services.news_service import get_recent_articles

router = APIRouter()


async def _get_all_stocks(db: AsyncSession) -> List[DashboardStockSchema]:
    results = []
    for symbol in settings.tracked_stocks:
        sent_stmt = (
            select(StockSentiment)
            .where(StockSentiment.symbol == symbol)
            .order_by(desc(StockSentiment.computed_at))
            .limit(1)
        )
        sent_row = await db.execute(sent_stmt)
        sentiment = sent_row.scalar_one_or_none()

        price_stmt = (
            select(StockPrice)
            .where(StockPrice.symbol == symbol)
            .order_by(desc(StockPrice.fetched_at))
            .limit(1)
        )
        price_row = await db.execute(price_stmt)
        price = price_row.scalar_one_or_none()

        results.append(DashboardStockSchema(
            symbol=symbol,
            price=price.price if price else 0.0,
            change=price.change if price else 0.0,
            change_pct=price.change_pct if price else 0.0,
            volume=price.volume if price else 0.0,
            sentiment_label=sentiment.sentiment_label if sentiment else "neutral",
            sentiment_score=sentiment.sentiment_score if sentiment else 0.0,
            signal=sentiment.signal if sentiment else "Hold",
            gpt_reasoning=sentiment.gpt_reasoning if sentiment else None,
            article_count=sentiment.article_count if sentiment else 0,
            mention_count=sentiment.mention_count if sentiment else 0,
        ))
    return results


@router.get("/", response_model=List[DashboardStockSchema])
async def get_all_stocks(db: AsyncSession = Depends(get_db)):
    return await _get_all_stocks(db)


@router.get("/trending", response_model=List[TrendingStockSchema])
async def get_trending(db: AsyncSession = Depends(get_db)):
    stocks = await _get_all_stocks(db)
    trending = sorted(stocks, key=lambda x: x.mention_count, reverse=True)
    return [
        TrendingStockSchema(
            symbol=s.symbol,
            mention_count=s.mention_count,
            sentiment_label=s.sentiment_label,
            sentiment_score=s.sentiment_score,
        )
        for s in trending[:5]
    ]


@router.get("/{symbol}", response_model=StockDetailSchema)
async def get_stock_detail(symbol: str, db: AsyncSession = Depends(get_db)):
    symbol = symbol.upper()
    if symbol not in settings.tracked_stocks:
        raise HTTPException(status_code=404, detail=f"Symbol {symbol} not tracked")

    stocks = await _get_all_stocks(db)
    current = next((s for s in stocks if s.symbol == symbol), None)
    if not current:
        raise HTTPException(status_code=404, detail="No data for this symbol yet")

    price_history_rows = await get_price_history(db, symbol, limit=48)

    # Get matching sentiment history
    sent_stmt = (
        select(StockSentiment)
        .where(StockSentiment.symbol == symbol)
        .order_by(desc(StockSentiment.computed_at))
        .limit(48)
    )
    sent_result = await db.execute(sent_stmt)
    sent_rows = list(reversed(sent_result.scalars().all()))

    price_history = []
    for i, ph in enumerate(price_history_rows):
        sent_score = sent_rows[i].sentiment_score if i < len(sent_rows) else 0.0
        price_history.append(PriceHistoryPoint(
            time=ph.fetched_at,
            price=ph.price,
            sentiment_score=sent_score or 0.0,
        ))

    recent_news = await get_recent_articles(db, symbol=symbol, limit=20)

    return StockDetailSchema(
        symbol=symbol,
        current=current,
        price_history=price_history,
        recent_news=recent_news,
    )
