<div align="center">
  <br/>
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://img.shields.io/badge/🎧_PaperCast-1a1a2e?style=for-the-badge&labelColor=0f3460">
    <img src="https://img.shields.io/badge/🎧_PaperCast-1a1a2e?style=for-the-badge&labelColor=0f3460" alt="PaperCast" height="60">
  </picture>

  <p align="center">
    <strong>Turn arXiv papers into podcasts — listen, learn, stay current.</strong>
    <br />
    <em>AI-powered paper summaries · On‑demand audio · Daily fetching · Citation insights</em>
  </p>

  <p align="center">
    <a href="#-features"><strong>Features</strong></a> ·
    <a href="#-quick-start"><strong>Quick Start</strong></a> ·
    <a href="#-configuration"><strong>Configuration</strong></a> ·
    <a href="#-api"><strong>API</strong></a> ·
    <a href="#-deployment"><strong>Deployment</strong></a> ·
    <a href="#-tech-stack"><strong>Tech Stack</strong></a>
  </p>

  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python&logoColor=white" alt="Python 3.11+">
    <img src="https://img.shields.io/badge/FastAPI-0.104+-009688?style=flat&logo=fastapi&logoColor=white" alt="FastAPI">
    <img src="https://img.shields.io/badge/SQLite-003B57?style=flat&logo=sqlite&logoColor=white" alt="SQLite">
    <img src="https://img.shields.io/badge/Docker-2496ED?style=flat&logo=docker&logoColor=white" alt="Docker">
    <img src="https://img.shields.io/badge/license-MIT-green?style=flat" alt="License">
  </p>

  <br/>
</div>

---

## ✨ Features

| Category | Capabilities |
|----------|-------------|
| **📥 Paper Ingestion** | Daily arXiv fetching by topic (AI, NLP, CV, Robotics). Scheduled updates via APScheduler. On‑demand manual refresh. |
| **🔊 Listen to Papers** | High‑quality TTS via **Microsoft Edge TTS** (free). Audio generated on‑demand & cached. Supports seek, speed control, next/prev track. |
| **🤖 AI Analysis** | DeepSeek‑powered paper summarization (answers 4 key questions about each paper in Chinese). Triggered per‑paper on demand. |
| **📊 Citation Insights** | Semantic Scholar integration for citation counts & influential citations. Sort by popularity. |
| **🔍 Search & Filter** | Full‑text search across titles & abstracts. Filter by topic, date, or favorites. |
| **📝 Personal Library** | Mark papers as read/listened. Star favorites. Add personal notes. |
| **💬 Inline Captions** | Real‑time sentence‑level highlighting during audio playback — follow along in the abstract. |
| **🎤 Voice Control** | Browser‑based speech recognition — say "play", "pause", "next", "slow down", etc. |
| **📱 PWA Ready** | Mobile‑friendly SPA. Installable as a Progressive Web App. |

## 🚀 Quick Start

### Prerequisites

- Python **3.11+**
- (Optional) [DeepSeek API key](https://platform.deepseek.com/) for AI analysis

### Install & Run

```bash
# 1. Clone the repository
git clone https://github.com/yourusername/papercast.git
cd papercast

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) Set DeepSeek API key for AI analysis
#    export DEEPSEEK_API_KEY="sk-..."

# 4. Start the server
python start.py
```

The first run initializes the database, fetches papers from arXiv, and starts the web server at **http://localhost:8000**.

### Docker

```bash
docker build -t papercast .
docker run -p 8000:8000 -e DEEPSEEK_API_KEY="sk-..." papercast
```

## ⚙️ Configuration

All settings live in [`backend/config.py`](backend/config.py):

```python
# arXiv topics to track
TOPICS = {
    "cs.AI": "Artificial Intelligence",
    "cs.CL": "Computation & Language (NLP)",
    "cs.CV": "Computer Vision",
    "cs.RO": "Robotics (Autonomous Driving)",
}

# TTS voice (Microsoft Edge TTS)
TTS_VOICE = "en-US-JennyNeural"

# Schedule (UTC)
FETCH_HOUR = 14  # runs daily at 14:00 UTC
```

| Variable | Default | Description |
|----------|---------|-------------|
| `TOPICS` | AI, NLP, CV, Robotics | arXiv categories to track |
| `ARXIV_MAX_RESULTS` | 100 | Max papers per category per query |
| `TTS_VOICE` | `en-US-JennyNeural` | edge‑tts voice |
| `TTS_SPEED` | `+0%` | Speech rate adjustment |
| `FETCH_HOUR` | `14` | Daily fetch time (UTC) |
| `FETCH_DAYS_BACK` | `7` | How far back to look for new papers |
| `DEEPSEEK_API_KEY` | `""` | Set via env var for AI analysis |

## 📡 API

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/topics` | List available arXiv topics |
| `GET` | `/api/papers` | Browse papers (filter: `topic`, `date`, `sort`, `favorited`) |
| `GET` | `/api/search?q=...` | Full‑text search across titles & abstracts |
| `GET` | `/api/papers/{id}` | Paper detail with full abstract |
| `GET` | `/api/audio/{id}` | Stream audio (supports `Range` header for seeking) |
| `POST` | `/api/refresh` | Trigger manual paper fetch |
| `POST` | `/api/papers/{id}/analyze` | Run DeepSeek AI analysis on a paper |
| `POST` | `/api/papers/{id}/read` | Mark paper as read |
| `POST` | `/api/papers/{id}/favorite` | Toggle favorite status |
| `PUT` | `/api/papers/{id}/notes` | Save personal notes |
| `GET` | `/api/status` | Server stats & last fetch info |

## 🏗️ Project Structure

```
papercast/
├── backend/
│   ├── main.py            # FastAPI app & all API routes
│   ├── config.py          # Settings (topics, voice, paths)
│   ├── database.py        # SQLite CRUD operations
│   ├── models.py          # Data models (Paper, Topic, FetchLog)
│   ├── arxiv_fetcher.py   # arXiv API client
│   ├── tts_engine.py      # edge‑tts audio generation
│   ├── ai_analysis.py     # DeepSeek Q&A analysis
│   ├── scholar_api.py     # Semantic Scholar citation fetcher
│   └── scheduler.py       # Daily fetch + audio cleanup scheduler
├── frontend/
│   └── index.html         # Single‑page application (full frontend)
├── data/
│   ├── audio/             # Generated MP3 files
│   └── papers.db          # SQLite database
├── start.py               # Entry point
├── setup.py               # One‑click setup script
├── Dockerfile             # Container build
├── render.yaml            # Render deployment config
└── requirements.txt       # Python dependencies
```

## 🐳 Deployment

### Docker

```bash
docker build -t papercast .
docker run -p 8000:8000 -e DEEPSEEK_API_KEY="sk-..." papercast
```

### Render (Free Tier)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy)

The included [`render.yaml`](render.yaml) configures everything — just set the `DEEPSEEK_API_KEY` environment variable.

> **Note:** Render's free tier uses an ephemeral filesystem. The SQLite database and audio files will be lost on each redeploy. For persistent storage, attach a [Render Disk](https://render.com/docs/disks) or use an external database.

## 🧰 Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/) |
| **Database** | [SQLite](https://www.sqlite.org/) (WAL mode) |
| **Paper Source** | [arXiv API](https://info.arxiv.org/help/api/index.html) |
| **Text‑to‑Speech** | [edge‑tts](https://github.com/rany2/edge-tts) (Microsoft Edge TTS) |
| **AI Analysis** | [DeepSeek](https://platform.deepseek.com/) (OpenAI‑compatible API) |
| **Citations** | [Semantic Scholar API](https://api.semanticscholar.org/) |
| **Scheduling** | [APScheduler](https://apscheduler.readthedocs.io/) |
| **Frontend** | Vanilla JS SPA (no framework) with CSS custom properties |
| **Audio Streaming** | MP3 with `Range` header support |
| **Voice Control** | Web Speech API (`SpeechRecognition`) |
| **Container** | Docker + Render |

## 📄 License

MIT — use it, modify it, share it.

---

<div align="center">
  <p>
    Made with ❤️ for researchers who'd rather <em>listen</em> than read.
    <br/>
    <sub>PaperCast — arXiv, but make it a podcast.</sub>
  </p>
</div>
