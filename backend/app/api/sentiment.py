from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db, AsyncSessionLocal
from app.schemas.schemas import StockSentimentSchema
from app.services.analysis_service import run_full_analysis

router = APIRouter()


@router.get("/", response_model=List[StockSentimentSchema])
async def get_sentiments(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select, desc
    from app.models.models import StockSentiment
    from app.core.config import settings

    results = []
    for symbol in settings.tracked_stocks:
        stmt = (
            select(StockSentiment)
            .where(StockSentiment.symbol == symbol)
            .order_by(desc(StockSentiment.computed_at))
            .limit(1)
        )
        row = await db.execute(stmt)
        s = row.scalar_one_or_none()
        if s:
            results.append(s)
    return results


@router.post("/refresh")
async def trigger_refresh(background_tasks: BackgroundTasks):
    """Manually trigger a full analysis refresh."""
    async def _run():
        async with AsyncSessionLocal() as db:
            await run_full_analysis(db)

    background_tasks.add_task(_run)
    return {"message": "Analysis refresh triggered", "status": "running"}
