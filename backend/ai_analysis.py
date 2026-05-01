"""AI-powered paper analysis using DeepSeek (OpenAI-compatible) API.

Analyzes a single paper on-demand, answering in Chinese:
  Q1: What problem does the paper solve?
  Q2: What related work exists?
  Q3: How does the paper solve the problem?
  Q5: What future work is suggested?

Returns a dict with keys q1, q2, q3, q5.
"""

import asyncio
import json
import logging
from typing import Dict, Optional

import aiohttp

from .config import DEEPSEEK_API_BASE, DEEPSEEK_API_KEY, DEEPSEEK_MODEL
from .models import Paper

logger = logging.getLogger(__name__)

TIMEOUT = 90  # seconds
SYSTEM_PROMPT = (
    "你是一个论文分析助手。请用中文回答用户关于论文的问题。"
    "回答要简洁、准确、有深度，每个问题控制在100-200字以内。"
)


def _build_prompt(paper: Paper) -> str:
    """Build a Chinese prompt for single-paper Q&A."""
    return (
        f"请根据以下论文信息，用中文回答下列问题。\n\n"
        f"论文标题：{paper.title}\n"
        f"论文摘要：{paper.abstract}\n\n"
        f"请回答以下问题：\n"
        f"Q1: 这篇论文试图解决什么问题？\n"
        f"Q2: 有哪些相关研究？\n"
        f"Q3: 论文如何解决这个问题？\n"
        f"Q5: 有什么可以进一步探索的点？\n\n"
        f"请以JSON格式返回，不要包含其他内容：\n"
        f'{{"q1": "...", "q2": "...", "q3": "...", "q5": "..."}}'
    )


def _parse_response(text: str) -> Optional[Dict[str, str]]:
    """Parse the JSON response, handling markdown code blocks."""
    text = text.strip()
    # Try direct JSON parse first
    if text.startswith("{"):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

    # Try extracting from ```json ... ``` block
    import re

    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(1).strip())
        except json.JSONDecodeError:
            pass

    # Try finding any JSON object
    m = re.search(r"\{[\s\S]*\}", text)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            pass

    return None


async def analyze_paper(paper: Paper) -> Optional[Dict[str, str]]:
    """Analyze a single paper with DeepSeek, returning Q1-Q5 answers.

    Args:
        paper: The Paper object to analyze.

    Returns:
        Dict with keys q1, q2, q3, q5 (Chinese text), or None on failure.
    """
    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY not set — skipping analysis")
        return None

    prompt = _build_prompt(paper)

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 2048,
    }

    url = f"{DEEPSEEK_API_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    logger.info("Analyzing paper %s with DeepSeek...", paper.id)

    try:
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=TIMEOUT),
        ) as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(
                        "DeepSeek returned HTTP %d for %s: %s",
                        resp.status, paper.id, body[:300],
                    )
                    return None

                data = await resp.json()

        # Extract response text
        content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
        if not content:
            logger.warning("DeepSeek returned empty response for %s", paper.id)
            return None

        finish_reason = data.get("choices", [{}])[0].get("finish_reason", "")
        if finish_reason == "length":
            logger.warning(
                "DeepSeek response was truncated for %s (max_tokens)", paper.id
            )

        # Parse JSON
        parsed = _parse_response(content)
        if not parsed:
            logger.warning(
                "Could not parse DeepSeek response as JSON for %s", paper.id
            )
            logger.debug("Raw response: %s", content[:500])
            return None

        # Validate required keys
        result = {}
        for key in ("q1", "q2", "q3", "q5"):
            result[key] = parsed.get(key, "")

        if not any(result.values()):
            logger.warning("DeepSeek response missing all Q&A keys for %s", paper.id)
            return None

        logger.info("Analysis complete for paper %s", paper.id)
        return result

    except asyncio.TimeoutError:
        logger.warning("DeepSeek request timed out for %s", paper.id)
        return None
    except aiohttp.ClientError as e:
        logger.warning("DeepSeek connection error for %s: %s", paper.id, e)
        return None
    except Exception as e:
        logger.warning("DeepSeek analysis failed for %s: %s", paper.id, e)
        return None
