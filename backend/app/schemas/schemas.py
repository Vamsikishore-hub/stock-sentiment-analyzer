from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List


class StockPriceSchema(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: float
    market_cap: Optional[float]
    fetched_at: datetime

    class Config:
        from_attributes = True


class NewsArticleSchema(BaseModel):
    id: int
    title: str
    description: Optional[str]
    url: Optional[str]
    source: Optional[str]
    published_at: Optional[datetime]
    related_symbols: Optional[str]
    sentiment_label: Optional[str]
    sentiment_score: Optional[float]
    is_reddit: bool
    created_at: datetime

    class Config:
        from_attributes = True


class StockSentimentSchema(BaseModel):
    symbol: str
    sentiment_label: str
    sentiment_score: float
    signal: str
    finbert_score: Optional[float]
    gpt_reasoning: Optional[str]
    article_count: int
    mention_count: int
    computed_at: datetime

    class Config:
        from_attributes = True


class MacroEventSchema(BaseModel):
    id: int
    event_type: Optional[str]
    summary: str
    gpt_analysis: str
    affected_symbols: Optional[str]
    impact: Optional[str]
    computed_at: datetime

    class Config:
        from_attributes = True


class DashboardStockSchema(BaseModel):
    symbol: str
    price: float
    change: float
    change_pct: float
    volume: float
    sentiment_label: str
    sentiment_score: float
    signal: str
    gpt_reasoning: Optional[str]
    article_count: int
    mention_count: int


class TrendingStockSchema(BaseModel):
    symbol: str
    mention_count: int
    sentiment_label: str
    sentiment_score: float


class PriceHistoryPoint(BaseModel):
    time: datetime
    price: float
    sentiment_score: float


class StockDetailSchema(BaseModel):
    symbol: str
    current: DashboardStockSchema
    price_history: List[PriceHistoryPoint]
    recent_news: List[NewsArticleSchema]
