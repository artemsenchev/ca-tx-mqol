"""Make `src` importable when running pytest from a clean checkout.

`pip install -e .` also works; this means the tests run without it.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
