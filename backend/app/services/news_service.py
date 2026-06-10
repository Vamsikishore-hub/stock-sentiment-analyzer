import httpx
import asyncio
import logging
import re
from datetime import datetime
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.models.models import NewsArticle
from app.core.config import settings

logger = logging.getLogger(__name__)

# Company name → ticker mapping for smart matching
COMPANY_NAMES = {
    "AAPL":  ["apple inc", "apple's", "apple computer", "tim cook"],
    "GOOGL": ["alphabet", "google llc", "google cloud", "google search",
              "google ads", "google play", "waymo", "deepmind", "sundar pichai"],
    "META":  ["meta platforms", "facebook", "instagram", "whatsapp", "oculus",
              "mark zuckerberg", "meta ai", "threads"],
    "AMZN":  ["amazon.com", "amazon web services", "aws", "amazon prime",
              "amazon fresh", "andy jassy", "amazon kindle"],
    "NFLX":  ["netflix", "netflix original", "netflix series", "reed hastings"],
    "TSLA":  ["tesla inc", "tesla motor", "elon musk", "cybertruck",
              "tesla energy", "gigafactory", "tesla ev"],
    "MSFT":  ["microsoft", "azure", "windows", "xbox", "github",
              "satya nadella", "bing", "copilot", "office 365"],
    "NVDA":  ["nvidia", "geforce", "cuda", "jensen huang", "rtx",
              "nvidia gpu", "h100", "blackwell"],
    "AMD":   ["advanced micro devices", "amd ryzen", "amd radeon",
              "lisa su", "epyc", "amd cpu", "amd gpu"],
    "ORCL":  ["oracle corp", "oracle cloud", "oracle database",
              "larry ellison", "oracle erp", "java oracle"],
}

NOISE_DOMAINS = [
    "pypi.org", "softpedia.com", "slickdeals.net", "rlsbb.to",
    "drivers.softpedia.com", "github.com", "stackoverflow.com",
    "hackernews",
]

FINANCIAL_CONTEXT = [
    "stock", "share", "earnings", "revenue", "profit", "loss", "quarter",
    "market", "investor", "analyst", "forecast", "guidance", "valuation",
    "ipo", "acquisition", "merger", "buyout", "dividend", "sec", "nasdaq",
    "nyse", "trading", "price target", "downgrade", "upgrade", "buy rating",
    "sell rating", "wall street", "hedge fund", "portfolio", "billion",
    "million", "growth", "decline", "competition", "regulatory", "antitrust",
    "layoff", "hire", "ceo", "cfo", "executive", "product launch", "ai",
    "cloud", "data center", "semiconductor", "chip", "gpu", "revenue",
    "investment", "funding", "valuation", "partnership", "deal",
]


def _is_noise_source(url: str) -> bool:
    if not url:
        return False
    return any(domain in url.lower() for domain in NOISE_DOMAINS)


def _has_financial_context(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in FINANCIAL_CONTEXT)


def _extract_symbols_smart(title: str, description: str, url: str) -> str:
    if _is_noise_source(url):
        return ""

    combined_text = f"{title} {description or ''}".lower()
    title_lower = title.lower()

    if not _has_financial_context(combined_text):
        return ""

    found = []
    for symbol in settings.tracked_stocks:
        matched = False

        ticker_pattern = r'(?<![A-Z$])' + re.escape(symbol) + r'(?![A-Z])'
        dollar_pattern = r'\$' + re.escape(symbol) + r'\b'

        if re.search(dollar_pattern, title, re.IGNORECASE):
            matched = True
        elif re.search(ticker_pattern, title):
            matched = True

        if not matched:
            for name in COMPANY_NAMES.get(symbol, []):
                if name in title_lower:
                    matched = True
                    break

        if not matched and description:
            desc_lower = description.lower()
            financial_hits = sum(1 for kw in FINANCIAL_CONTEXT if kw in combined_text)
            if financial_hits >= 2:
                for name in COMPANY_NAMES.get(symbol, []):
                    if name in desc_lower:
                        matched = True
                        break

        if matched:
            found.append(symbol)

    return ",".join(found)


async def fetch_all_news() -> List[Dict]:
    """Fetch financial headlines from NewsAPI only."""
    articles = []
    query = " OR ".join([
        "Apple stock", "Google Alphabet", "Meta Platforms", "Amazon AWS",
        "Netflix earnings", "Tesla stock", "Microsoft Azure",
        "NVIDIA GPU", "AMD chips", "Oracle cloud",
        "AAPL", "GOOGL", "META", "AMZN", "NFLX",
        "TSLA", "MSFT", "NVDA", "AMD", "ORCL"
    ])

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": query,
                    "language": "en",
                    "sortBy": "publishedAt",
                    "pageSize": 100,
                    "apiKey": settings.newsapi_key,
                }
            )
            resp.raise_for_status()
            data = resp.json()

        for art in data.get("articles", []):
            title = art.get("title") or ""
            description = art.get("description") or ""
            url = art.get("url") or ""

            symbols = _extract_symbols_smart(title, description, url)
            if not symbols:
                continue

            published_str = art.get("publishedAt")
            published_at = None
            if published_str:
                try:
                    published_at = datetime.fromisoformat(published_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            articles.append({
                "title": title,
                "description": description[:500] if description else None,
                "url": url,
                "source": art.get("source", {}).get("name"),
                "published_at": published_at,
                "related_symbols": symbols,
                "is_reddit": False,
            })

    except Exception as e:
        logger.error(f"NewsAPI fetch error: {e}")

    logger.info(f"Smart filter: kept {len(articles)} relevant articles")
    return articles


async def save_articles(db: AsyncSession, articles: List[Dict]) -> int:
    saved = 0
    for art in articles:
        stmt = select(NewsArticle).where(NewsArticle.title == art["title"]).limit(1)
        existing = await db.execute(stmt)
        if existing.scalar_one_or_none():
            continue
        record = NewsArticle(**art)
        db.add(record)
        saved += 1
    await db.commit()
    return saved


async def get_recent_articles(
    db: AsyncSession,
    symbol: Optional[str] = None,
    limit: int = 50,
) -> List[NewsArticle]:
    stmt = select(NewsArticle).order_by(desc(NewsArticle.published_at)).limit(limit)
    if symbol:
        stmt = stmt.where(NewsArticle.related_symbols.contains(symbol))
    result = await db.execute(stmt)
    return result.scalars().all()
