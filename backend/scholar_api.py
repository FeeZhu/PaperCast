"""Semantic Scholar API client for fetching citation counts."""

import asyncio
import logging
import re
from typing import Dict, List, Tuple

import aiohttp

logger = logging.getLogger(__name__)

BATCH_URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
FIELDS = "citationCount,influentialCitationCount"
TIMEOUT = 30  # seconds
MAX_RETRIES = 3


def _strip_version(arxiv_id: str) -> str:
    """Remove version suffix from arXiv ID (e.g. '2301.12345v1' -> '2301.12345')."""
    return re.sub(r'v\d+$', '', arxiv_id)


async def fetch_citations(
    arxiv_ids: List[str],
) -> Dict[str, Tuple[int, int]]:
    """Fetch citation counts for a list of arXiv IDs using Semantic Scholar batch API.

    Args:
        arxiv_ids: List of arXiv paper IDs (e.g. ["2301.12345v1", "2301.12346v1"])

    Returns:
        Dict mapping the original paper ID -> (citation_count, influential_citation_count)
    """
    if not arxiv_ids:
        return {}

    # Deduplicate and build mapping: version-less ID -> original IDs
    id_map: Dict[str, List[str]] = {}
    for pid in arxiv_ids:
        base = _strip_version(pid)
        id_map.setdefault(base, []).append(pid)

    result: Dict[str, Tuple[int, int]] = {}

    # Process in batches of 50 (API limit)
    batch_size = 50
    bases = list(id_map.keys())
    logger.debug(
        "Fetching citations for %d unique arXiv IDs (from %d total): %s...",
        len(bases), len(arxiv_ids),
        bases[:3] if len(bases) > 3 else bases,
    )

    for i in range(0, len(bases), batch_size):
        batch_bases = bases[i : i + batch_size]
        try:
            batch_result = await _fetch_batch(batch_bases)
            # Apply result to all original IDs matching each base
            for base, counts in batch_result.items():
                for original_id in id_map.get(base, []):
                    result[original_id] = counts
        except Exception as e:
            logger.warning(
                "Semantic Scholar batch failed for %d papers: %s",
                len(batch_bases), e,
            )

    return result


async def _fetch_batch(bases: List[str]) -> Dict[str, Tuple[int, int]]:
    """Fetch a single batch from Semantic Scholar (version-less base IDs).

    Uses arXiv: prefix (lowercase) as required by Semantic Scholar API.
    """
    # Prefix arXiv IDs with Semantic Scholar's required format
    ids = [f"arXiv:{base}" for base in bases]

    payload = {"ids": ids}
    url = f"{BATCH_URL}?fields={FIELDS}"

    logger.debug("Sending request to Semantic Scholar with %d IDs", len(ids))
    logger.debug("First few IDs: %s", ids[:3])

    for attempt in range(MAX_RETRIES):
        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=TIMEOUT),
            ) as session:
                async with session.post(url, json=payload) as resp:
                    if resp.status == 429:
                        wait = 5 * (attempt + 1)
                        logger.warning(
                            "Semantic Scholar rate limited (429), "
                            "retrying in %ds (attempt %d/%d)",
                            wait, attempt + 1, MAX_RETRIES,
                        )
                        await asyncio.sleep(wait)
                        continue

                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(
                            "Semantic Scholar returned HTTP %d (attempt %d/%d): %s",
                            resp.status, attempt + 1, MAX_RETRIES, body[:500],
                        )
                        if attempt + 1 < MAX_RETRIES:
                            await asyncio.sleep(2)
                            continue
                        return {}

                    data = await resp.json()

            result: Dict[str, Tuple[int, int]] = {}
            for item, base in zip(data, bases):
                if item is None:
                    logger.debug("Paper %s not found in Semantic Scholar", base)
                    continue
                ext_ids = item.get("externalIds", {})
                if ext_ids.get("ArXiv"):
                    c_count = item.get("citationCount", 0) or 0
                    ic_count = item.get("influentialCitationCount", 0) or 0
                    result[base] = (int(c_count), int(ic_count))
                else:
                    logger.debug(
                        "Paper %s found but no ArXiv externalId: %s",
                        base, ext_ids,
                    )

            logger.debug(
                "Semantic Scholar batch: got %d results out of %d requested",
                len(result), len(bases),
            )
            return result

        except asyncio.TimeoutError:
            logger.warning(
                "Semantic Scholar request timed out (attempt %d/%d)",
                attempt + 1, MAX_RETRIES,
            )
            if attempt + 1 < MAX_RETRIES:
                await asyncio.sleep(2)
                continue
            return {}

        except aiohttp.ClientError as e:
            logger.warning(
                "Semantic Scholar connection error (attempt %d/%d): %s",
                attempt + 1, MAX_RETRIES, e,
            )
            if attempt + 1 < MAX_RETRIES:
                await asyncio.sleep(2)
                continue
            return {}

        except Exception as e:
            logger.warning(
                "Semantic Scholar unexpected error (attempt %d/%d): %s",
                attempt + 1, MAX_RETRIES, e,
            )
            return {}

    return {}
