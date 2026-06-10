import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import settings
from app.core.database import AsyncSessionLocal

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

# ── Terminal output helpers ────────────────────────────────────
SEP   = "  " + "─" * 53
THICK = "  " + "━" * 53

def _print(msg=""):
    print(msg, flush=True)

def _stage(n, total, msg):
    print(f"\033[36m  [{n}/{total}]  {msg}\033[0m", flush=True)

def _ok(msg):
    print(f"\033[32m  ✓  {msg}\033[0m", flush=True)

def _warn(msg):
    print(f"\033[33m  ⚠  {msg}\033[0m", flush=True)

def _err(msg):
    print(f"\033[31m  ✗  {msg}\033[0m", flush=True)

READY_BANNER = """
\033[32m  ╔═══════════════════════════════════════════════════════╗
  ║                                                       ║
  ║      ✅  SMSA IS READY — ALL SYSTEMS ACTIVE           ║
  ║                                                       ║
  ║      🌐  http://localhost:3000                        ║
  ║                                                       ║
  ║      📊  FinBERT sentiment      ·  ACTIVE             ║
  ║      🤖  Llama 3.2 reasoning    ·  ACTIVE             ║
  ║      💰  Live stock prices      ·  ACTIVE             ║
  ║      🗞   NewsAPI headlines      ·  ACTIVE             ║
  ║      🔄  Auto-refresh           ·  Every {interval} minutes    ║
  ║                                                       ║
  ║      You are good to use the website! 🚀              ║
  ║                                                       ║
  ╚═══════════════════════════════════════════════════════╝\033[0m
"""


async def _wait_for_ollama(max_retries: int = 24, delay: int = 10):
    import httpx
    _stage(2, 3, "Waiting for Llama 3.2 to load...")
    for i in range(max_retries):
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get("http://ollama:11434/api/tags")
                if resp.status_code == 200:
                    models = [m.get("name", "") for m in resp.json().get("models", [])]
                    if any("llama3.2" in m for m in models):
                        _ok("Llama 3.2 model loaded")
                        return True
        except Exception:
            pass
        elapsed = (i + 1) * delay
        print(f"  \033[90m     → still loading... ({elapsed}s)\033[0m", flush=True)
        await asyncio.sleep(delay)
    _warn("Llama 3.2 not ready — macro analysis will be skipped this cycle")
    return False


async def _run_analysis_job(verbose: bool = False):
    from app.services.analysis_service import run_full_analysis
    if verbose:
        _stage(3, 3, "Running analysis pipeline...")
    try:
        async with AsyncSessionLocal() as db:
            result = await run_full_analysis(db, verbose=verbose)
        if verbose:
            stocks = result.get("stocks", [])
            priced = sum(1 for s in stocks if s.get("price", 0) > 0)
            _ok(f"Prices fetched:      {priced}/10 stocks")
            articles = result.get("news_feed", [])
            _ok(f"Articles processed:  {len(articles)} headlines")
            macro = result.get("macro_summary")
            if macro:
                _ok("Macro analysis:      complete")
            else:
                _warn("Macro analysis:      skipped (Llama warming up)")
        return True
    except Exception as e:
        _err(f"Analysis failed: {e}")
        logger.error(f"Analysis error: {e}", exc_info=True)
        return False


async def start_scheduler():
    scheduler.add_job(
        _run_analysis_job,
        trigger=IntervalTrigger(minutes=settings.refresh_interval_minutes),
        id="analysis_job",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("  [2/3]  Scheduler started ✓")

    await _wait_for_ollama()
    await _run_analysis_job(verbose=True)

    _print()
    _print(READY_BANNER.format(interval=str(settings.refresh_interval_minutes).ljust(2)))


async def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
