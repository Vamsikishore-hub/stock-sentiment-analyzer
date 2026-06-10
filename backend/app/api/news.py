from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.core.database import get_db
from app.schemas.schemas import NewsArticleSchema
from app.services.news_service import get_recent_articles

router = APIRouter()


@router.get("/", response_model=List[NewsArticleSchema])
async def get_news(
    symbol: Optional[str] = Query(None, description="Filter by stock symbol"),
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    articles = await get_recent_articles(db, symbol=symbol, limit=limit)
    return articles
