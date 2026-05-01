import py_compile
import sys

files = [
    r"f:\code\vibe_coding\papercast\backend\config.py",
    r"f:\code\vibe_coding\papercast\backend\models.py",
    r"f:\code\vibe_coding\papercast\backend\database.py",
    r"f:\code\vibe_coding\papercast\backend\arxiv_fetcher.py",
    r"f:\code\vibe_coding\papercast\backend\tts_engine.py",
    r"f:\code\vibe_coding\papercast\backend\scheduler.py",
    r"f:\code\vibe_coding\papercast\backend\main.py",
]

all_ok = True
for f in files:
    try:
        py_compile.compile(f, doraise=True)
        print(f"OK: {f}")
    except py_compile.PyCompileError as e:
        print(f"ERROR: {f}")
        print(f"  {e}")
        all_ok = False

if all_ok:
    print("\nAll files passed syntax check.")
    sys.exit(0)
else:
    print("\nSome files have syntax errors.")
    sys.exit(1)
