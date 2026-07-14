"""Make modules under ``src/`` importable in tests as top-level modules."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))
