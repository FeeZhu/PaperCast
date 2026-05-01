"""Application configuration."""

import os
from pathlib import Path

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
AUDIO_DIR = DATA_DIR / "audio"
DB_PATH = DATA_DIR / "papers.db"

# arXiv topics to track
# Format: {category_code: display_name}
TOPICS = {
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation & Language (NLP)",
    "cs.CV": "Computer Vision",
    "cs.RO": "Robotics (Autonomous Driving)",
}

# arXiv API settings
ARXIV_API_BASE = "http://export.arxiv.org/api/query"
ARXIV_MAX_RESULTS = 100  # max papers per category per query

# TTS settings
TTS_VOICE = "en-US-JennyNeural"  # edge-tts voice
TTS_SPEED = "+0%"  # speech speed adjustment

# Scheduler settings
FETCH_HOUR = 14  # UTC hour to run daily fetch (14:00 UTC = ~22:00 Beijing)
FETCH_DAYS_BACK = 7  # how many days back to look for new papers

# Web server
HOST = "0.0.0.0"
PORT = 8000

# AI Analysis (DeepSeek / OpenAI-compatible API)
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
DEEPSEEK_API_BASE = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-v4-flash"
