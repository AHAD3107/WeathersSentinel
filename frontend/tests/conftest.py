"""Pytest fixtures and environment setup for frontend tests."""

import sys
from pathlib import Path

# Ensure frontend root is in sys.path
frontend_root = str(Path(__file__).resolve().parent.parent)
if frontend_root not in sys.path:
    sys.path.insert(0, frontend_root)
