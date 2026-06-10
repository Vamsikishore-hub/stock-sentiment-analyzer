import asyncio
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

_pipeline = None


def _get_pipeline():
    global _pipeline
    if _pipeline is None:
        try:
            from transformers import pipeline
            logger.info("Loading FinBERT model...")
            _pipeline = pipeline(
                "text-classification",
                model="ProsusAI/finbert",
                tokenizer="ProsusAI/finbert",
                top_k=None,
                device=-1,
            )
            logger.info("FinBERT loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load FinBERT: {e}")
            _pipeline = None
    return _pipeline


def _finbert_label_to_sentiment(label: str, score: float) -> Tuple[str, float]:
    """
    FinBERT outputs: positive / negative / neutral
    We map to:       bullish  / bearish  / neutral
    with signed score -1.0 to +1.0
    """
    label = label.lower()
    if label == "positive":
        return "bullish", score
    elif label == "negative":
        return "bearish", -score
    else:
        return "neutral", 0.0


def _run_finbert(texts: List[str]) -> List[Tuple[str, float]]:
    pipe = _get_pipeline()
    if pipe is None:
        return [("neutral", 0.0)] * len(texts)

    results = []
    chunk_size = 16
    for i in range(0, len(texts), chunk_size):
        chunk = [t[:512] for t in texts[i:i + chunk_size]]
        try:
            outputs = pipe(chunk)
            for output in outputs:
                best = max(output, key=lambda x: x["score"])
                label, score = _finbert_label_to_sentiment(best["label"], best["score"])
                results.append((label, score))
        except Exception as e:
            logger.error(f"FinBERT inference error: {e}")
            results.extend([("neutral", 0.0)] * len(chunk))

    return results


async def analyze_headlines(texts: List[str]) -> List[Tuple[str, float]]:
    if not texts:
        return []
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _run_finbert, texts)


def aggregate_sentiment(scores: List[float]) -> Tuple[str, float]:
    if not scores:
        return ("neutral", 0.0)
    avg = max(-1.0, min(1.0, sum(scores) / len(scores)))
    if avg >= 0.15:
        label = "bullish"
    elif avg <= -0.15:
        label = "bearish"
    else:
        label = "neutral"
    return label, round(avg, 4)


def score_to_signal(sentiment_label: str, sentiment_score: float) -> str:
    if sentiment_label == "bullish" and sentiment_score >= 0.25:
        return "Buy"
    elif sentiment_label == "bearish" and sentiment_score <= -0.25:
        return "Sell"
    else:
        return "Hold"


# Suppress tokenizer future warnings
import warnings
warnings.filterwarnings("ignore", category=FutureWarning, module="transformers")
