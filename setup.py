"""PaperCast setup script.
Run: python setup.py
"""

import os
import struct
import subprocess
import sys
import zlib
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
REQUIREMENTS = BASE_DIR / "requirements.txt"
FRONTEND_ASSETS = BASE_DIR / "frontend" / "assets"
AUDIO_DIR = BASE_DIR / "data" / "audio"


def step(msg):
    print(f"\n{'='*50}")
    print(f"  {msg}")
    print(f"{'='*50}")


def run_pip():
    """Install Python dependencies."""
    step("[1/4] Installing Python dependencies...")

    # Try various pip locations
    pip_candidates = [
        [sys.executable, "-m", "pip"],
        [str(Path(sys.executable).parent / "pip"), "install"],
        ["D:/conda/Scripts/pip.exe", "install"],
        ["pip", "install"],
    ]

    for base_cmd in pip_candidates:
        cmd = base_cmd + ["-r", str(REQUIREMENTS)]
        print(f"  Trying: {' '.join(cmd)}")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            if result.returncode == 0:
                print(f"  ✓ Success!")
                return True
            else:
                print(f"  ✗ Failed: {result.stderr[:200]}")
        except FileNotFoundError:
            print(f"  ✗ Command not found")
            continue

    print("  ✗ All pip install attempts failed.")
    print("  Please run manually: pip install -r requirements.txt")
    return False


def setup_icons():
    """Create placeholder icons for the PWA manifest."""
    step("[2/4] Setting up app icons...")
    FRONTEND_ASSETS.mkdir(parents=True, exist_ok=True)

    icon_192 = FRONTEND_ASSETS / "icon-192.png"
    icon_512 = FRONTEND_ASSETS / "icon-512.png"

    # Create placeholders if missing
    for target, size in [(icon_192, 192), (icon_512, 512)]:
        if not target.exists():
            print(f"  Creating placeholder icon: {target.name} ({size}x{size})")
            try:
                _create_placeholder_png(str(target), size)
                print(f"  ✓ Created {target.name}")
            except Exception as e:
                print(f"  ✗ Failed to create {target.name}: {e}")


def _create_placeholder_png(path, size):
    """Create a simple solid-color PNG file."""
    def create_chunk(ctype, data):
        chunk = ctype + data
        return (
            struct.pack(">I", len(data))
            + chunk
            + struct.pack(">I", zlib.crc32(chunk) & 0xFFFFFFFF)
        )

    header = b"\x89PNG\r\n\x1a\n"
    ihdr = create_chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 2, 0, 0, 0))

    raw = b""
    for _ in range(size):
        raw += b"\x00"  # filter byte
        raw += b"\x0f\x0f\x1a" * size  # dark navy pixels

    idat = create_chunk(b"IDAT", zlib.compress(raw))
    iend = create_chunk(b"IEND", b"")

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(header + ihdr + idat + iend)


def setup_directories():
    """Create required data directories."""
    step("[3/4] Creating data directories...")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  ✓ {AUDIO_DIR}")
    print(f"  ✓ {AUDIO_DIR.parent / 'papers.db'} (will be created on first run)")


def print_summary():
    """Print final instructions."""
    step("[4/4] Setup complete!")
    print()
    print(f"  To start PaperCast, run:")
    print()
    print(f"      cd /d {BASE_DIR}")
    print(f"      python start.py")
    print()
    print(f"  Then open: http://localhost:8000")
    print()


if __name__ == "__main__":
    print()
    print("  ╔══════════════════════════════════════╗")
    print("  ║        PaperCast - Setup             ║")
    print("  ╚══════════════════════════════════════╝")

    run_pip()
    setup_icons()
    setup_directories()
    print_summary()
