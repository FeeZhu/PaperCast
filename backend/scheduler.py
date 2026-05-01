"""Scheduler for daily arXiv paper fetching and audio cleanup."""

import asyncio
import logging
from pathlib import Path
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .arxiv_fetcher import fetch_all_topics
from .config import FETCH_HOUR
from .database import (
    get_audio_before_date, get_papers_without_citations, log_fetch,
    mark_audio_stale, update_citations,
)
from .scholar_api import fetch_citations

logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler = AsyncIOScheduler()


async def _cleanup_yesterday_audio():
    """Delete audio files from previous days and reset DB status."""
    today_str = date.today().isoformat()  # e.g. "2026-05-02"
    old_audio = get_audio_before_date(today_str)
    if not old_audio:
        return

    deleted_count = 0
    for paper in old_audio:
        if paper.audio_path:
            audio_file = Path(paper.audio_path)
            try:
                if audio_file.exists():
                    audio_file.unlink()
                    deleted_count += 1
            except Exception as e:
                logger.warning(
                    "Failed to delete audio for %s: %s", paper.id, e
                )
        mark_audio_stale(paper.id)

    if deleted_count:
        logger.info(
            "Cleaned %d audio files from previous days", deleted_count,
        )


async def _run_fetch():
    """Clean up yesterday's audio, fetch new papers, refresh citations."""
    logger.info("Scheduled fetch: starting...")

    # Step 1: Clean up previous day's audio cache
    await _cleanup_yesterday_audio()

    # Step 2: Fetch new papers
    try:
        new_papers = await asyncio.to_thread(fetch_all_topics)
        log_fetch(len(new_papers), "success")
        logger.info("Scheduled fetch: got %d new papers", len(new_papers))
    except Exception as e:
        logger.error("Scheduled fetch failed: %s", e, exc_info=True)
        log_fetch(0, "error", str(e))

    # Step 3: Refresh citation data for papers without it
    await _refresh_citations()


async def _refresh_citations():
    """Fetch citation counts for papers that don't have them yet."""
    papers = get_papers_without_citations(limit=200)
    if not papers:
        return

    arxiv_ids = [p.id for p in papers]
    logger.info("Refreshing citations for %d papers...", len(arxiv_ids))

    citations = await fetch_citations(arxiv_ids)
    if not citations:
        return

    updated = 0
    for arxiv_id, (c_count, ic_count) in citations.items():
        update_citations(arxiv_id, c_count, ic_count)
        updated += 1

    logger.info("Citation refresh: updated %d papers", updated)


def start_scheduler():
    """Start the background scheduler."""
    trigger = CronTrigger(hour=FETCH_HOUR, minute=0)
    scheduler.add_job(
        _run_fetch,
        trigger=trigger,
        id="daily_arxiv_fetch",
        name="Daily arXiv paper fetch & audio cleanup",
        replace_existing=True,
    )

    scheduler.start()
    logger.info(
        "Scheduler started. Daily fetch at UTC %d:00 (cleans previous day's audio)",
        FETCH_HOUR,
    )


async def run_manual_fetch():
    """Manually trigger a paper fetch (with citation refresh)."""
    logger.info("Manual refresh triggered")

    result = {}
    try:
        new_papers = await asyncio.to_thread(fetch_all_topics)
        log_fetch(len(new_papers), "success")
        result = {"status": "success", "new_papers": len(new_papers)}
    except Exception as e:
        logger.error("Manual refresh failed: %s", e, exc_info=True)
        log_fetch(0, "error", str(e))
        result = {"status": "error", "message": str(e)}

    # Also refresh citations
    await _refresh_citations()

    return result


def shutdown_scheduler():
    """Shut down the scheduler gracefully."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down")
