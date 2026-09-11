"""Bootstrap: adds project root to sys.path for scripts.

Import this at the top of every script:
    import _bootstrap  # noqa: F401
"""

import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))