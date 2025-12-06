"""
Pytest configuration file.
This makes sure the project root is on sys.path so that
modules under `src/` can be imported in tests like:
    from src.calculations import Calculator
"""
import os
import sys

# Determine the project root (one level above /tests)
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# Add the root directory to sys.path so that "import src.xxx" works in tests
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)
