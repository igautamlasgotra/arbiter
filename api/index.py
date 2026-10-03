"""Vercel entrypoint.

Vercel serves this file as the single function behind every route (see the
rewrite in vercel.json), so the whole FastAPI app is reachable from one
deployment. The app itself knows nothing about Vercel - it is the same object
uvicorn serves locally, which is what keeps the hosted demo and the laptop
demo identical.
"""

from __future__ import annotations

import sys
from pathlib import Path

# The function's working directory is not guaranteed to be on sys.path, and
# `arbiter` lives at the repository root next to this file's parent.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from arbiter.web.app import app  # noqa: E402

__all__ = ["app"]
