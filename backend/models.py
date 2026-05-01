"""Data models for PaperCast."""

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional


@dataclass
class Paper:
    """Represents an arXiv paper."""
    id: str  # arXiv ID (e.g., "2301.12345")
    title: str
    authors: str  # comma-separated
    abstract: str
    categories: str  # comma-separated
    published: date
    updated: Optional[date] = None
    link: str = ""
    audio_path: Optional[str] = None
    audio_duration: Optional[float] = None  # seconds
    audio_generated: bool = False
    audio_created_at: Optional[datetime] = None  # when audio was generated (for TTL)
    citation_count: int = 0  # from Semantic Scholar
    influential_citation_count: int = 0  # from Semantic Scholar
    citation_updated_at: Optional[datetime] = None  # when citation data was fetched
    ai_analysis: str = ""  # JSON: {q1, q2, q3, q5} in Chinese
    ai_analyzed_at: Optional[datetime] = None  # when AI analysis was done
    is_read: bool = False
    is_favorited: bool = False
    notes: str = ""
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if not self.link:
            self.link = f"https://arxiv.org/abs/{self.id}"


@dataclass
class Topic:
    """Represents an arXiv topic/category."""
    code: str  # e.g., "cs.AI"
    name: str
    enabled: bool = True


@dataclass
class FetchLog:
    """Log entry for a fetch operation."""
    id: Optional[int] = None
    fetched_at: Optional[datetime] = None
    papers_count: int = 0
    status: str = "success"  # success, error
    error_message: Optional[str] = None
