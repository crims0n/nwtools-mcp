"""Compatibility shim for legacy imports and execution."""

from pathlib import Path
import sys

SRC_PATH = Path(__file__).resolve().parent / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from nwtools_mcp.main import run


if __name__ == "__main__":
    run()
