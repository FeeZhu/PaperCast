"""FastAPI application for PaperCast."""

import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse

from .config import AUDIO_DIR, HOST, PORT
from .database import (
    get_paper,
    get_papers,
    get_stats,
    get_topics,
    init_db,
    mark_paper_read,
    search_papers,
    toggle_favorite,
    update_audio_status,
    update_notes,
)
from .scheduler import run_manual_fetch, start_scheduler
from .tts_engine import generate_audio, get_audio_duration

logger = logging.getLogger(__name__)

app = FastAPI(title="PaperCast", version="2.0.0")


# ─── Lifespan ────────────────────────────────────────────


@app.on_event("startup")
async def startup():
    """Initialize the application."""
    init_db()
    logger.info("Database initialized")

    start_scheduler()
    logger.info("Scheduler started")

    AUDIO_DIR.mkdir(parents=True, exist_ok=True)


@app.on_event("shutdown")
async def shutdown():
    """Clean shutdown."""
    from .scheduler import shutdown_scheduler
    shutdown_scheduler()


# ─── API Routes ──────────────────────────────────────────


def _paper_to_dict(p, full_abstract=False):
    """Convert a Paper object to a JSON-serializable dict."""
    d = {
        "id": p.id,
        "title": p.title,
        "authors": p.authors,
        "abstract": p.abstract,
        "categories": p.categories,
        "published": p.published.isoformat(),
        "link": p.link,
        "audio_generated": p.audio_generated,
        "audio_duration": p.audio_duration,
        "is_read": p.is_read,
        "is_favorited": p.is_favorited,
        "notes": p.notes,
        "citation_count": p.citation_count,
        "influential_citation_count": p.influential_citation_count,
        "ai_analysis": p.ai_analysis,
        "ai_analyzed_at": p.ai_analyzed_at.isoformat() if p.ai_analyzed_at else None,
    }
    return d


@app.get("/api/topics")
async def api_topics():
    """Get all available topics."""
    topics = get_topics()
    return [{"code": t.code, "name": t.name} for t in topics]


@app.get("/api/papers")
async def api_papers(
    topic: Optional[str] = Query(None),
    date: Optional[str] = Query(None),
    sort: str = Query("date", regex="^(date|popular)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    favorited: bool = Query(False),
):
    """Get papers with optional filtering and sorting."""
    papers, total = get_papers(
        topic=topic, date_str=date, sort=sort, page=page, limit=limit,
        favorited_only=favorited,
    )
    return {
        "papers": [_paper_to_dict(p) for p in papers],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
    }


@app.get("/api/search")
async def api_search(
    q: str = Query(..., min_length=1),
    topic: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    """Search papers by keyword in title/abstract."""
    papers, total = search_papers(
        query=q, topic=topic, page=page, limit=limit
    )
    return {
        "papers": [_paper_to_dict(p) for p in papers],
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit if total > 0 else 1,
        "query": q,
    }


@app.get("/api/papers/{paper_id}")
async def api_paper_detail(paper_id: str):
    """Get full paper details."""
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _paper_to_dict(paper, full_abstract=True)


@app.get("/api/audio/{paper_id}")
async def api_audio(paper_id: str, request: Request):
    """Stream audio for a paper. Generates audio on-demand if not cached."""
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    audio_path = Path(paper.audio_path) if paper.audio_path else None

    # Generate audio on-demand if not available or file missing
    if not audio_path or not audio_path.exists():
        logger.info("Generating audio on-demand for %s", paper_id)
        audio_path = await generate_audio(
            text=paper.abstract,
            paper_id=paper.id,
            title=paper.title,
        )
        if not audio_path:
            raise HTTPException(
                status_code=500, detail="Failed to generate audio"
            )

        duration = await get_audio_duration(audio_path)
        update_audio_status(
            paper_id=paper.id,
            audio_path=str(audio_path),
            duration=duration or 0,
        )

    file_size = audio_path.stat().st_size
    range_header = request.headers.get("range")

    if range_header:
        start, end = 0, file_size - 1
        range_val = range_header.replace("bytes=", "")
        if "-" in range_val:
            parts = range_val.split("-")
            if parts[0]:
                start = int(parts[0])
            if parts[1]:
                end = int(parts[1])

        if start >= file_size:
            raise HTTPException(
                status_code=416,
                detail=f"Range not satisfiable: {start} >= {file_size}",
            )

        end = min(end, file_size - 1)
        content_length = end - start + 1

        async def ranged_stream():
            with open(audio_path, "rb") as f:
                f.seek(start)
                remaining = content_length
                while remaining > 0:
                    chunk_size = min(65536, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            ranged_stream(),
            status_code=206,
            media_type="audio/mpeg",
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Content-Length": str(content_length),
                "Accept-Ranges": "bytes",
            },
        )
    else:
        return FileResponse(
            audio_path,
            media_type="audio/mpeg",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
            },
        )


@app.post("/api/refresh")
async def api_refresh():
    """Manually trigger paper fetch (no audio generation)."""
    result = await run_manual_fetch()
    return result


@app.post("/api/papers/{paper_id}/analyze")
async def api_analyze_paper(paper_id: str):
    """Analyze a single paper with DeepSeek (Q1-Q5 in Chinese)."""
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")

    from .ai_analysis import analyze_paper
    from .database import update_paper_analysis

    result = await analyze_paper(paper)
    if not result:
        raise HTTPException(
            status_code=500,
            detail="AI analysis failed. Check that DEEPSEEK_API_KEY is set.",
        )

    # Save to database
    import json
    update_paper_analysis(paper_id, json.dumps(result, ensure_ascii=False))

    return result


@app.post("/api/papers/{paper_id}/read")
async def api_mark_read(paper_id: str):
    """Mark a paper as read/listened."""
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    mark_paper_read(paper_id)
    return {"status": "ok"}


@app.post("/api/papers/{paper_id}/favorite")
async def api_toggle_favorite(paper_id: str):
    """Toggle the favorite status of a paper."""
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    new_status = toggle_favorite(paper_id)
    return {"is_favorited": new_status}


@app.put("/api/papers/{paper_id}/notes")
async def api_update_notes(paper_id: str, request: Request):
    """Update notes for a paper."""
    paper = get_paper(paper_id)
    if not paper:
        raise HTTPException(status_code=404, detail="Paper not found")
    body = await request.json()
    notes = body.get("notes", "")
    update_notes(paper_id, notes)
    return {"status": "ok"}


@app.get("/api/status")
async def api_status():
    """Get server and data status."""
    stats = get_stats()
    return stats


# ─── Frontend ────────────────────────────────────────────


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the frontend SPA."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return HTMLResponse("<h1>PaperCast</h1><p>Frontend not built yet.</p>")
    return index_path.read_text(encoding="utf-8")


@app.get("/assets/{filepath:path}")
async def serve_asset(filepath: str):
    """Serve frontend assets."""
    asset_path = FRONTEND_DIR / "assets" / filepath
    if not asset_path.exists():
        raise HTTPException(status_code=404)
    return FileResponse(asset_path)


# ─── Main ────────────────────────────────────────────────


def run():
    """Run the application with uvicorn."""
    import uvicorn

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    uvicorn.run(
        "backend.main:app",
        host=HOST,
        port=PORT,
        reload=False,
        log_level="info",
        loop="asyncio",
        timeout_keep_alive=60,
    )


if __name__ == "__main__":
    run()
