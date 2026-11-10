#!/usr/bin/env python3
"""CLI wrapper for pdownloader-mcp."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from scripts.pdownloader_mcp import main

if __name__ == "__main__":
    main()
