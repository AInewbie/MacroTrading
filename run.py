#!/usr/bin/env python3
"""Zero-install launcher: Python 3.11+ only."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))
from macrotrading.server import main

if __name__ == "__main__":
    main()
