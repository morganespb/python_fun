"""idea bench

python main.py        start at the first sketch, then use the arrow keys
python main.py 7      start at sketch 7
"""
import importlib
import sys

from core.app import run
from sketches import SKETCHES


def loader(file, cls):
    # sketches are only imported when you reach them, so the window opens fast
    return lambda: getattr(importlib.import_module(f"sketches.{file}"), cls)


if __name__ == "__main__":
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run([loader(f, c) for f, c in SKETCHES], start)
