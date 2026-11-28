"""Explicit startup command for an input-independent studio session; no startup hook is installed."""
from pathlib import Path
import sys

directory = str(Path(__file__).resolve().parent)
if directory not in sys.path:
    sys.path.insert(0, directory)
import studio_session
studio_session.start()
