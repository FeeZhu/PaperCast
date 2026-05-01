"""SQLite database operations for PaperCast."""

import sqlite3
import logging
from contextlib import contextmanager
from datetime import date, datetime
from typing import List, Optional, Tuple

from .config import DB_PATH
from .models import FetchLog, Paper, Topic

logger = logging.getLogger(__name__)


def init_db():
    """Initialize the database, creating tables if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS papers (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                authors TEXT NOT NULL DEFAULT '',
                abstract TEXT NOT NULL DEFAULT '',
                categories TEXT NOT NULL DEFAULT '',
                published TEXT NOT NULL,
                updated TEXT,
                link TEXT NOT NULL DEFAULT '',
                audio_path TEXT,
                audio_duration REAL,
                audio_generated INTEGER NOT NULL DEFAULT 0,
                is_read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS topics (
                code TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS fetch_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now')),
                papers_count INTEGER NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'success',
                error_message TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published);
            CREATE INDEX IF NOT EXISTS idx_papers_categories ON papers(categories);
            CREATE INDEX IF NOT EXISTS idx_papers_audio_gen ON papers(audio_generated);
        """)
        # Add audio_created_at column for existing databases (migration)
        try:
            conn.execute(
                "ALTER TABLE papers ADD COLUMN audio_created_at TEXT"
            )
        except sqlite3.OperationalError:
            pass  # column already exists
        # Add citation columns for existing databases (migration)
        for col in ["citation_count", "influential_citation_count", "citation_updated_at"]:
            try:
                conn.execute(
                    f"ALTER TABLE papers ADD COLUMN {col} INTEGER NOT NULL DEFAULT 0"
                    if col != "citation_updated_at"
                    else f"ALTER TABLE papers ADD COLUMN {col} TEXT"
                )
            except sqlite3.OperationalError:
                pass  # column already exists
        # Add AI analysis columns for existing databases (migration)
        for col in ["ai_analysis", "ai_analyzed_at"]:
            try:
                type_sql = "TEXT"
                conn.execute(f"ALTER TABLE papers ADD COLUMN {col} {type_sql}")
            except sqlite3.OperationalError:
                pass  # column already exists
        # Add is_favorited and notes columns
        for col in ["is_favorited", "notes"]:
            try:
                type_sql = "INTEGER NOT NULL DEFAULT 0" if col == "is_favorited" else "TEXT DEFAULT ''"
                conn.execute(f"ALTER TABLE papers ADD COLUMN {col} {type_sql}")
            except sqlite3.OperationalError:
                pass  # column already exists
        row = conn.execute("SELECT COUNT(*) FROM topics").fetchone()
        if row[0] == 0:
            from .config import TOPICS
            for code, name in TOPICS.items():
                conn.execute(
                    "INSERT OR IGNORE INTO topics (code, name) VALUES (?, ?)",
                    (code, name),
                )


@contextmanager
def get_conn():
    """Get a database connection (context manager).
    Auto-commits on success, rolls back on exception.
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─── Paper CRUD ──────────────────────────────────────────


def paper_from_row(row) -> Paper:
    """Convert a sqlite3.Row to a Paper object."""
    return Paper(
        id=row["id"],
        title=row["title"],
        authors=row["authors"],
        abstract=row["abstract"],
        categories=row["categories"],
        published=date.fromisoformat(row["published"]),
        updated=date.fromisoformat(row["updated"]) if row["updated"] else None,
        link=row["link"],
        audio_path=row["audio_path"],
        audio_duration=row["audio_duration"],
        audio_generated=bool(row["audio_generated"]),
        audio_created_at=(
            datetime.fromisoformat(row["audio_created_at"])
            if row["audio_created_at"]
            else None
        ),
        is_read=bool(row["is_read"]),
        is_favorited=bool(row["is_favorited"]),
        notes=row["notes"] or "",
        citation_count=int(row["citation_count"]) if row["citation_count"] else 0,
        influential_citation_count=int(row["influential_citation_count"]) if row["influential_citation_count"] else 0,
        citation_updated_at=(
            datetime.fromisoformat(row["citation_updated_at"])
            if row["citation_updated_at"]
            else None
        ),
        ai_analysis=row["ai_analysis"] or "",
        ai_analyzed_at=(
            datetime.fromisoformat(row["ai_analyzed_at"])
            if row["ai_analyzed_at"]
            else None
        ),
        created_at=(
            datetime.fromisoformat(row["created_at"])
            if row["created_at"]
            else None
        ),
    )


def upsert_paper(paper: Paper) -> bool:
    """Insert or update a paper. Returns True if inserted (new), False if updated."""
    with get_conn() as conn:
        existing = conn.execute(
            "SELECT id FROM papers WHERE id = ?", (paper.id,)
        ).fetchone()
        conn.execute(
            """INSERT OR REPLACE INTO papers
               (id, title, authors, abstract, categories, published, updated, link,
                audio_path, audio_duration, audio_generated, audio_created_at,
                citation_count, influential_citation_count, citation_updated_at,
                ai_analysis, ai_analyzed_at,
                is_read, is_favorited, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                paper.id,
                paper.title,
                paper.authors,
                paper.abstract,
                paper.categories,
                paper.published.isoformat(),
                paper.updated.isoformat() if paper.updated else None,
                paper.link,
                paper.audio_path,
                paper.audio_duration,
                int(paper.audio_generated),
                paper.audio_created_at.isoformat() if paper.audio_created_at else None,
                paper.citation_count,
                paper.influential_citation_count,
                paper.citation_updated_at.isoformat() if paper.citation_updated_at else None,
                paper.ai_analysis,
                paper.ai_analyzed_at.isoformat() if paper.ai_analyzed_at else None,
                int(paper.is_read),
                int(paper.is_favorited),
                paper.notes,
            ),
        )
        return existing is None


def get_papers(
    topic: Optional[str] = None,
    date_str: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
    sort: str = "date",
    favorited_only: bool = False,
) -> Tuple[List[Paper], int]:
    """Get papers with optional filtering and pagination.

    Args:
        sort: "date" (default, newest first) or "popular" (by citation count)
        favorited_only: only return favorited papers
    Returns (papers, total_count).
    """
    conditions = []
    params = []

    if topic:
        conditions.append("categories LIKE ?")
        params.append(f"%{topic}%")

    if date_str:
        conditions.append("published = ?")
        params.append(date_str)

    if favorited_only:
        conditions.append("is_favorited = 1")

    where = " AND ".join(conditions) if conditions else "1=1"

    with get_conn() as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) FROM papers WHERE {where}", params
        ).fetchone()
        total = count_row[0]

        offset = (page - 1) * limit
        if sort == "popular":
            order_clause = "ORDER BY citation_count DESC, influential_citation_count DESC"
        else:
            order_clause = "ORDER BY published DESC, id DESC"
        rows = conn.execute(
            f"SELECT * FROM papers WHERE {where} {order_clause} LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    papers = [paper_from_row(r) for r in rows]
    return papers, total


def get_paper(paper_id: str) -> Optional[Paper]:
    """Get a single paper by ID."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
    return paper_from_row(row) if row else None


def get_papers_without_audio(limit: int = 10) -> List[Paper]:
    """Get papers that haven't had audio generated yet."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM papers WHERE audio_generated = 0 ORDER BY published DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [paper_from_row(r) for r in rows]


def update_audio_status(
    paper_id: str, audio_path: str, duration: float
):
    """Mark a paper as having audio generated (or refreshed)."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET audio_generated = 1, audio_path = ?, audio_duration = ?, audio_created_at = ? WHERE id = ?",
            (audio_path, duration, now, paper_id),
        )


def update_citations(paper_id: str, citation_count: int, influential_citation_count: int):
    """Update citation data for a paper."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET citation_count = ?, influential_citation_count = ?, citation_updated_at = ? WHERE id = ?",
            (citation_count, influential_citation_count, now, paper_id),
        )


def get_papers_without_citations(limit: int = 200) -> List[Paper]:
    """Get papers that haven't had citation data fetched yet."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM papers WHERE citation_count = 0 AND citation_updated_at IS NULL ORDER BY published DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [paper_from_row(r) for r in rows]


def update_paper_analysis(paper_id: str, analysis_json: str):
    """Store per-paper AI analysis (Q1-Q5 JSON) and update analyzed timestamp."""
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET ai_analysis = ?, ai_analyzed_at = ? WHERE id = ?",
            (analysis_json, now, paper_id),
        )


def mark_audio_stale(paper_id: str):
    """Mark a paper's audio as expired/stale."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET audio_generated = 0, audio_path = NULL, audio_duration = NULL, audio_created_at = NULL WHERE id = ?",
            (paper_id,),
        )


def get_audio_before_date(date_str: str) -> List[Paper]:
    """Get papers with audio generated before a given date."""
    with get_conn() as conn:
        rows = conn.execute(
            """SELECT * FROM papers
               WHERE audio_generated = 1
               AND audio_created_at IS NOT NULL
               AND audio_created_at < ?
               LIMIT 200""",
            (date_str,),
        ).fetchall()
    return [paper_from_row(r) for r in rows]


def search_papers(
    query: str,
    topic: Optional[str] = None,
    page: int = 1,
    limit: int = 20,
) -> Tuple[List[Paper], int]:
    """Search papers by keyword in title/abstract, optionally filtered by topic."""
    conditions = ["(title LIKE ? OR abstract LIKE ?)"]
    params = [f"%{query}%", f"%{query}%"]

    if topic:
        conditions.append("categories LIKE ?")
        params.append(f"%{topic}%")

    where = " AND ".join(conditions)

    with get_conn() as conn:
        count_row = conn.execute(
            f"SELECT COUNT(*) FROM papers WHERE {where}", params
        ).fetchone()
        total = count_row[0]

        offset = (page - 1) * limit
        rows = conn.execute(
            f"SELECT * FROM papers WHERE {where} ORDER BY published DESC, id DESC LIMIT ? OFFSET ?",
            params + [limit, offset],
        ).fetchall()

    papers = [paper_from_row(r) for r in rows]
    return papers, total


def mark_paper_read(paper_id: str):
    """Mark a paper as read/listened."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET is_read = 1 WHERE id = ?", (paper_id,)
        )


def toggle_favorite(paper_id: str) -> bool:
    """Toggle the favorite status of a paper. Returns the new status."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT is_favorited FROM papers WHERE id = ?", (paper_id,)
        ).fetchone()
        if row is None:
            return False
        new_val = 0 if row["is_favorited"] else 1
        conn.execute(
            "UPDATE papers SET is_favorited = ? WHERE id = ?",
            (new_val, paper_id),
        )
        return bool(new_val)


def update_notes(paper_id: str, notes: str):
    """Update notes for a paper."""
    with get_conn() as conn:
        conn.execute(
            "UPDATE papers SET notes = ? WHERE id = ?",
            (notes, paper_id),
        )


# ─── Topic operations ────────────────────────────────────


def get_topics() -> List[Topic]:
    """Get all enabled topics."""
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM topics WHERE enabled = 1 ORDER BY code"
        ).fetchall()
    return [Topic(code=r["code"], name=r["name"]) for r in rows]


# ─── Fetch log ───────────────────────────────────────────


def log_fetch(papers_count: int, status: str = "success", error: Optional[str] = None):
    """Record a fetch operation in the log."""
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO fetch_log (papers_count, status, error_message) VALUES (?, ?, ?)",
            (papers_count, status, error),
        )


def get_last_fetch() -> Optional[FetchLog]:
    """Get the most recent fetch log entry."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM fetch_log ORDER BY fetched_at DESC LIMIT 1"
        ).fetchone()
    if row:
        return FetchLog(
            id=row["id"],
            fetched_at=datetime.fromisoformat(row["fetched_at"]),
            papers_count=row["papers_count"],
            status=row["status"],
            error_message=row["error_message"],
        )
    return None


def get_stats() -> dict:
    """Get summary statistics."""
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM papers").fetchone()[0]
        with_audio = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE audio_generated = 1"
        ).fetchone()[0]
        today = date.today().isoformat()
        today_count = conn.execute(
            "SELECT COUNT(*) FROM papers WHERE published = ?", (today,)
        ).fetchone()[0]
        last_fetch = get_last_fetch()
    return {
        "total_papers": total,
        "with_audio": with_audio,
        "today_papers": today_count,
        "last_fetch": last_fetch,
    }
