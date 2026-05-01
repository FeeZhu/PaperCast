# PaperCast - Listen to arXiv Papers

## Setup

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
python start.py
```

Then open http://localhost:8000 in your browser.

## Dependencies

- fastapi - Web framework
- uvicorn - ASGI server
- arxiv - arXiv API client
- edge-tts - Microsoft Edge TTS (free, high quality)
- apscheduler - Daily task scheduling
- aiofiles - Async file operations

## Project Structure

```
papercast/
├── backend/
│   ├── main.py            # FastAPI app + API routes
│   ├── config.py          # Settings (topics, paths)
│   ├── database.py        # SQLite operations
│   ├── models.py          # Data models
│   ├── arxiv_fetcher.py   # arXiv API client
│   ├── tts_engine.py      # edge-tts wrapper
│   └── scheduler.py        # Daily fetch scheduler
├── frontend/
│   └── index.html         # SPA (audio player + paper browser)
├── data/
│   ├── audio/             # Generated MP3 files
│   └── papers.db          # SQLite database
├── start.py               # Entry point
└── requirements.txt
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/topics | List topics |
| GET | /api/papers | List papers (query: topic, date, page, limit) |
| GET | /api/papers/{id} | Paper detail with full abstract |
| GET | /api/audio/{id} | Stream audio (supports Range for seeking) |
| POST | /api/refresh | Trigger manual fetch |
| POST | /api/papers/{id}/read | Mark paper as read |
| GET | /api/status | Server stats |

## Config

Edit `backend/config.py` to:
- Change arXiv topics (TOPICS dict)
- Adjust TTS voice (TTS_VOICE)
- Change fetch schedule (FETCH_HOUR)
- Set server host/port
