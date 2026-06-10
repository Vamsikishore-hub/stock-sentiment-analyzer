import asyncio
import logging
import httpx
import time
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.models import StockPrice
from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Alpha Vantage ────────────────────────────────────────────
# Free key at https://www.alphavantage.co/support/#api-key
# 25 requests/day on free tier — enough for startup + a few refreshes
# Set ALPHA_VANTAGE_KEY in your .env file
AV_URL = "https://www.alphavantage.co/query"

# ── Fallback: Yahoo Finance query1 (different subdomain, less blocked) ──
YAHOO_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
YAHOO_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://finance.yahoo.com",
}


def _fetch_via_alpha_vantage(symbols: List[str], api_key: str) -> List[Dict]:
    """Alpha Vantage BATCH quote — 1 request for all symbols."""
    results = []
    try:
        # BATCH_STOCK_QUOTES endpoint — fetches up to 100 symbols in 1 call
        symbols_str = ",".join(symbols)
        resp = httpx.get(
            AV_URL,
            params={
                "function": "BATCH_STOCK_QUOTES",
                "symbols": symbols_str,
                "apikey": api_key,
            },
            timeout=20,
        )
        data = resp.json()
        for quote in data.get("Stock Quotes", []):
            symbol = quote.get("1. symbol")
            price = float(quote.get("2. price") or 0)
            if symbol and price > 0:
                results.append({
                    "symbol": symbol,
                    "price": round(price, 2),
                    "change": 0.0,
                    "change_pct": 0.0,
                    "volume": float(quote.get("3. volume") or 0),
                    "market_cap": None,
                    "fetched_at": datetime.utcnow(),
                })
                logger.info(f"✓ {symbol} = ${price:.2f} (AlphaVantage)")
    except Exception as e:
        logger.error(f"Alpha Vantage batch failed: {e}")

    # If batch didn't work (deprecated endpoint), try per-symbol GLOBAL_QUOTE
    fetched = {r["symbol"] for r in results}
    missing = [s for s in symbols if s not in fetched]
    if missing and api_key:
        for symbol in missing:
            try:
                resp = httpx.get(
                    AV_URL,
                    params={
                        "function": "GLOBAL_QUOTE",
                        "symbol": symbol,
                        "apikey": api_key,
                    },
                    timeout=15,
                )
                data = resp.json()
                quote = data.get("Global Quote", {})
                price = float(quote.get("05. price") or 0)
                prev = float(quote.get("08. previous close") or price)
                change = float(quote.get("09. change") or 0)
                change_pct_str = quote.get("10. change percent", "0%").replace("%", "")
                change_pct = float(change_pct_str or 0)

                if price > 0:
                    results.append({
                        "symbol": symbol,
                        "price": round(price, 2),
                        "change": round(change, 2),
                        "change_pct": round(change_pct, 2),
                        "volume": float(quote.get("06. volume") or 0),
                        "market_cap": None,
                        "fetched_at": datetime.utcnow(),
                    })
                    logger.info(f"✓ {symbol} = ${price:.2f} ({change_pct:+.2f}%) (AV GLOBAL_QUOTE)")
                    time.sleep(0.5)  # Respect rate limit
            except Exception as e:
                logger.error(f"Alpha Vantage GLOBAL_QUOTE failed for {symbol}: {e}")

    return results


def _fetch_via_yahoo(symbols: List[str]) -> List[Dict]:
    """Yahoo Finance fallback with delay between requests."""
    results = []
    with httpx.Client(timeout=20, headers=YAHOO_HEADERS, follow_redirects=True) as client:
        try:
            client.get("https://finance.yahoo.com", timeout=8)
            time.sleep(1)
        except Exception:
            pass

        for symbol in symbols:
            try:
                resp = client.get(
                    YAHOO_URL.format(symbol=symbol),
                    params={"interval": "1d", "range": "5d"},
                )
                if resp.status_code == 200:
                    meta = resp.json().get("chart", {}).get("result", [{}])[0].get("meta", {})
                    price = float(meta.get("regularMarketPrice") or meta.get("previousClose") or 0)
                    prev = float(meta.get("previousClose") or price)
                    if price > 0:
                        change = price - prev
                        change_pct = (change / prev * 100) if prev else 0
                        results.append({
                            "symbol": symbol,
                            "price": round(price, 2),
                            "change": round(change, 2),
                            "change_pct": round(change_pct, 2),
                            "volume": float(meta.get("regularMarketVolume") or 0),
                            "market_cap": None,
                            "fetched_at": datetime.utcnow(),
                        })
                        logger.info(f"✓ {symbol} = ${price:.2f} (Yahoo)")
                time.sleep(0.8)
            except Exception as e:
                logger.error(f"Yahoo failed for {symbol}: {e}")
    return results


def _fetch_all_prices(symbols: List[str]) -> List[Dict]:
    av_key = settings.alpha_vantage_key

    # Try Alpha Vantage first if key is configured
    if av_key and av_key != "your_alpha_vantage_key_here":
        results = _fetch_via_alpha_vantage(symbols, av_key)
        if len(results) >= 8:  # Good enough
            return results
        # Fill missing with Yahoo
        fetched = {r["symbol"] for r in results}
        missing = [s for s in symbols if s not in fetched]
        if missing:
            yahoo_results = _fetch_via_yahoo(missing)
            results.extend(yahoo_results)
        return results

    # No AV key — use Yahoo with delays
    logger.info("No Alpha Vantage key set, using Yahoo Finance with delays...")
    return _fetch_via_yahoo(symbols)


async def fetch_prices(symbols: List[str]) -> List[Dict]:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _fetch_all_prices, symbols)


async def save_prices(db: AsyncSession, prices: List[Dict]) -> None:
    for p in prices:
        record = StockPrice(**p)
        db.add(record)
    await db.commit()


async def get_latest_prices(db: AsyncSession) -> List[StockPrice]:
    results = []
    for symbol in settings.tracked_stocks:
        stmt = (
            select(StockPrice)
            .where(StockPrice.symbol == symbol)
            .order_by(desc(StockPrice.fetched_at))
            .limit(1)
        )
        row = await db.execute(stmt)
        price = row.scalar_one_or_none()
        if price:
            results.append(price)
    return results


async def get_price_history(db: AsyncSession, symbol: str, limit: int = 48) -> List[StockPrice]:
    stmt = (
        select(StockPrice)
        .where(StockPrice.symbol == symbol)
        .order_by(desc(StockPrice.fetched_at))
        .limit(limit)
    )
    result = await db.execute(stmt)
    rows = result.scalars().all()
    return list(reversed(rows))
