from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from app.core.database import get_db
from app.models.models import MacroEvent
from app.schemas.schemas import MacroEventSchema

router = APIRouter()


@router.get("/", response_model=List[MacroEventSchema])
async def get_macro_events(db: AsyncSession = Depends(get_db)):
    stmt = select(MacroEvent).order_by(desc(MacroEvent.computed_at)).limit(10)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/latest")
async def get_latest_macro(db: AsyncSession = Depends(get_db)):
    """Get the most recent macro analysis summary."""
    stmt = select(MacroEvent).order_by(desc(MacroEvent.computed_at)).limit(1)
    result = await db.execute(stmt)
    event = result.scalar_one_or_none()
    if not event:
        return {"macro_summary": None, "events": []}

    all_stmt = (
        select(MacroEvent)
        .where(MacroEvent.computed_at >= event.computed_at)
        .order_by(desc(MacroEvent.computed_at))
        .limit(5)
    )
    all_result = await db.execute(all_stmt)
    events = all_result.scalars().all()

    return {
        "macro_summary": event.gpt_analysis,
        "events": [
            {
                "event_type": e.event_type,
                "summary": e.summary,
                "impact": e.impact,
                "affected_symbols": e.affected_symbols,
                "computed_at": e.computed_at.isoformat(),
            }
            for e in events
        ],
    }
