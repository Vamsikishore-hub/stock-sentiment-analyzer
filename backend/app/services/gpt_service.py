import asyncio
import logging
import json
import httpx
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Ollama runs as a sidecar container — free, local, no API key
OLLAMA_URL = "http://ollama:11434/api/generate"
MODEL = "llama3.2:3b"

SYSTEM_PROMPT = """You are a senior financial analyst. Analyze news headlines and return ONLY a JSON object.
No markdown. No explanation. No code fences. Raw JSON only."""


def _build_prompt(headlines: List[str], sentiment_scores: Dict[str, float], symbols: List[str]) -> str:
    headlines_text = "\n".join(f"- {h}" for h in headlines[:40])
    scores_text = "\n".join(f"  {sym}: {score:+.3f}" for sym, score in sentiment_scores.items())
    symbols_text = ", ".join(symbols)

    return f"""{SYSTEM_PROMPT}

Recent financial headlines:
{headlines_text}

FinBERT sentiment scores:
{scores_text}

Analyze the macro environment for: {symbols_text}

Return this exact JSON structure:
{{
  "macro_summary": "2-3 sentences on current market forces",
  "stock_reasoning": {{
    "AAPL": "brief bullish/bearish reason",
    "GOOGL": "brief bullish/bearish reason",
    "META": "brief bullish/bearish reason",
    "AMZN": "brief bullish/bearish reason",
    "NFLX": "brief bullish/bearish reason",
    "TSLA": "brief bullish/bearish reason",
    "MSFT": "brief bullish/bearish reason",
    "NVDA": "brief bullish/bearish reason",
    "AMD": "brief bullish/bearish reason",
    "ORCL": "brief bullish/bearish reason"
  }},
  "macro_events": [
    {{
      "event_type": "category",
      "summary": "what happened",
      "impact": "positive",
      "affected_symbols": "AAPL,MSFT"
    }}
  ]
}}"""


async def get_macro_analysis(
    headlines: List[str],
    sentiment_scores: Dict[str, float],
    symbols: List[str],
) -> Optional[Dict]:
    """Call local Ollama LLM for macro reasoning — free, no API key."""
    if not headlines:
        return None

    prompt = _build_prompt(headlines, sentiment_scores, symbols)

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                OLLAMA_URL,
                json={
                    "model": MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 1024,
                    }
                }
            )
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "")

        # Strip any accidental markdown fences
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        # Find JSON object boundaries
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start == -1 or end == 0:
            logger.error("No JSON object found in Ollama response")
            return None

        result = json.loads(raw[start:end])
        logger.info("Ollama macro analysis complete")
        return result

    except json.JSONDecodeError as e:
        logger.error(f"Ollama JSON parse error: {e}")
        return None
    except httpx.ConnectError:
        logger.warning("Ollama not reachable — macro analysis skipped")
        return None
    except Exception as e:
        logger.error(f"Ollama error: {e}")
        return None
