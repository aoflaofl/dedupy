"""
Test configuration for pytest.

Ensures the repository root is on sys.path so `import dedupy` works when running
tests from different working directories.
"""

import sys
from pathlib import Path

# Add project root to sys.path for imports
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
