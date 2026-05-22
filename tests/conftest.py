"""
Pytest configuration for Token Telemetry tests.

This ensures all tests import from the local src/ directory rather than
any installed package version.
"""

import os
import sys

# Add src directory to Python path so tests import the local version
# This must be done before any other imports
src_path = os.path.join(os.path.dirname(__file__), "..", "src")
if os.path.exists(src_path) and src_path not in sys.path:
    sys.path.insert(0, src_path)
