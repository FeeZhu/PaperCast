"""Text-to-Speech engine using edge-tts."""

import logging
from pathlib import Path
from typing import Optional

import edge_tts

from .config import AUDIO_DIR, TTS_SPEED, TTS_VOICE

logger = logging.getLogger(__name__)


async def generate_audio(
    text: str,
    paper_id: str,
    title: str,
    voice: str = TTS_VOICE,
    speed: str = TTS_SPEED,
) -> Optional[Path]:
    """Generate audio from text using edge-tts.

    Args:
        text: The text to convert to speech
        paper_id: arXiv paper ID (used for filename)
        title: Paper title (used for display/reference)
        voice: edge-tts voice name
        speed: Speed adjustment string (e.g., '+0%', '+20%')

    Returns:
        Path to the generated audio file, or None on failure
    """
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)

    filename = f"{paper_id}.mp3"
    filepath = AUDIO_DIR / filename

    # Skip if already exists
    if filepath.exists():
        logger.info("Audio already exists for %s: %s", paper_id, filepath)
        return filepath

    # Build the communicate text with a brief intro
    speak_text = f"{title}. {text}"

    try:
        communicate = edge_tts.Communicate(speak_text, voice, rate=speed)
        await communicate.save(str(filepath))

        size_kb = filepath.stat().st_size / 1024
        logger.info(
            "Generated audio for %s: %s (%.1f KB)",
            paper_id, filepath, size_kb,
        )
        return filepath

    except Exception as e:
        logger.error(
            "Failed to generate audio for %s: %s", paper_id, e, exc_info=True
        )
        # Clean up partial file
        if filepath.exists():
            filepath.unlink()
        return None


async def get_audio_duration(filepath: Path) -> Optional[float]:
    """Get audio duration in seconds by parsing the MP3.

    Uses a simple approximation based on file size and bitrate.
    edge-tts produces ~32kbps MP3 files.
    """
    try:
        size_bytes = filepath.stat().st_size
        # edge-tts uses ~32kbps CBR
        estimated_bitrate = 32000  # bits per second
        duration = (size_bytes * 8) / estimated_bitrate
        return round(duration, 1)
    except Exception as e:
        logger.warning("Could not estimate duration for %s: %s", filepath, e)
        return None
