from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, Index
from sqlalchemy.sql import func
from app.core.database import Base


class StockPrice(Base):
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    price = Column(Float, nullable=False)
    change = Column(Float, default=0.0)
    change_pct = Column(Float, default=0.0)
    volume = Column(Float, default=0.0)
    market_cap = Column(Float, nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_stock_price_symbol_time", "symbol", "fetched_at"),
    )


class NewsArticle(Base):
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    source = Column(String(200), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True, index=True)
    related_symbols = Column(String(200), nullable=True)
    sentiment_label = Column(String(20), nullable=True)
    sentiment_score = Column(Float, nullable=True)
    is_reddit = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_news_symbol_time", "related_symbols", "published_at"),
    )


class StockSentiment(Base):
    __tablename__ = "stock_sentiments"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    sentiment_label = Column(String(20), nullable=False)
    sentiment_score = Column(Float, nullable=False)
    signal = Column(String(10), nullable=False)
    finbert_score = Column(Float, nullable=True)
    gpt_reasoning = Column(Text, nullable=True)
    article_count = Column(Integer, default=0)
    mention_count = Column(Integer, default=0)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_sentiment_symbol_time", "symbol", "computed_at"),
    )


class MacroEvent(Base):
    __tablename__ = "macro_events"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String(200), nullable=True)   # increased from 50
    summary = Column(Text, nullable=False)             # Text instead of VARCHAR
    gpt_analysis = Column(Text, nullable=False)
    affected_symbols = Column(String(200), nullable=True)
    impact = Column(String(20), nullable=True)
    computed_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
