"""arXiv API client for fetching papers."""

import logging
from datetime import date, datetime, timedelta
from typing import List

import arxiv

from .config import FETCH_DAYS_BACK, TOPICS
from .database import upsert_paper
from .models import Paper

logger = logging.getLogger(__name__)


def fetch_papers_for_topic(
    topic_code: str, max_results: int = 100, days_back: int = FETCH_DAYS_BACK
) -> List[Paper]:
    """Fetch recent papers for a given arXiv category.

    Args:
        topic_code: arXiv category code (e.g., 'cs.AI')
        max_results: Maximum number of results to fetch
        days_back: How many days back to search

    Returns:
        List of Paper objects that were newly inserted
    """
    cutoff_date = date.today() - timedelta(days=days_back)
    new_papers = []

    # Build search query: cat:cs.AI AND submittedDate:[YYYYMMDD TO YYYYMMDD]
    date_from = cutoff_date.strftime("%Y%m%d")
    date_to = date.today().strftime("%Y%m%d")
    query = f"cat:{topic_code} AND submittedDate:[{date_from} TO {date_to}]"

    logger.info(
        "Fetching papers for %s: query=%s, max=%d",
        topic_code, query, max_results,
    )

    try:
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )

        client = arxiv.Client()
        results = list(client.results(search))
        logger.info("Got %d results for %s", len(results), topic_code)

        for result in results:
            paper_id = result.entry_id.rstrip("/").split("/")[-1]
            # Handle arXiv ID with version (e.g., "2301.12345v1")
            if "v" in paper_id and paper_id.split("v")[-1].isdigit():
                # Keep the full ID with version for uniqueness
                pass

            # authors
            authors_str = ", ".join(
                [a.name for a in result.authors]
            )

            # categories
            categories_str = ", ".join(result.categories)

            # published date
            published = result.published.date() if hasattr(result.published, 'date') else result.published

            # updated date
            updated = None
            if hasattr(result, 'updated') and result.updated:
                updated = result.updated.date() if hasattr(result.updated, 'date') else result.updated

            paper = Paper(
                id=paper_id,
                title=result.title.replace("\n", " ").strip(),
                authors=authors_str,
                abstract=result.summary.replace("\n", " ").strip(),
                categories=categories_str,
                published=published,
                updated=updated,
                link=result.entry_id,
            )

            is_new = upsert_paper(paper)
            if is_new:
                new_papers.append(paper)

        logger.info(
            "Topic %s: %d new papers out of %d fetched",
            topic_code, len(new_papers), len(results),
        )

    except Exception as e:
        logger.error("Error fetching topic %s: %s", topic_code, e, exc_info=True)

    return new_papers


def fetch_all_topics(max_results: int = 100) -> List[Paper]:
    """Fetch papers for all configured topics.

    Returns:
        List of all newly inserted papers across all topics
    """
    all_new = []
    for topic_code in TOPICS:
        new_papers = fetch_papers_for_topic(topic_code, max_results)
        all_new.extend(new_papers)
    return all_new
