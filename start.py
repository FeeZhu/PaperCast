"""PaperCast - Listen to arXiv Papers.
Startup script that initializes the database and runs the server.
"""

import logging
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent / "backend"
sys.path.insert(0, str(backend_dir.parent))

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("papercast")

    # Ensure data directories exist
    from backend.config import AUDIO_DIR, DATA_DIR

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    from backend.database import init_db

    init_db()
    logger.info("Database initialized at %s", DATA_DIR / "papers.db")

    # Run initial fetch if DB is empty (no audio generation needed)
    from backend.database import get_stats

    stats = get_stats()
    if stats["total_papers"] == 0:
        logger.info("No papers found. Running initial fetch...")
        from backend.arxiv_fetcher import fetch_all_topics

        try:
            new_papers = fetch_all_topics()
            logger.info(
                "Initial fetch complete: %d new papers. Audio will be generated on-demand.",
                len(new_papers),
            )
        except Exception as e:
            logger.error("Initial fetch failed: %s", e)

    # Start the server
    from backend.main import run

    logger.info("Starting PaperCast server...")
    run()
