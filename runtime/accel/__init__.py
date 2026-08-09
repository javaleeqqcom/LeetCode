"""Optional CPython acceleration with a semantics-identical Python fallback."""

from __future__ import annotations

import os

from .fallback import DIGEST_SCHEME, legacy_digest_value


_mode = os.getenv("OJ_RUNTIME_ACCEL", "python").strip().lower()
if _mode not in {"1", "on", "true", "cython"}:
    from .fallback import digest_value

    HAS_ACCEL = False
    DIGEST_BACKEND = "python"
else:
    try:
        from ._result_digest import digest_value
    except ImportError:
        from .fallback import digest_value

        HAS_ACCEL = False
        DIGEST_BACKEND = "python"
    else:
        HAS_ACCEL = True
        DIGEST_BACKEND = "cython"


__all__ = [
    "DIGEST_BACKEND",
    "DIGEST_SCHEME",
    "HAS_ACCEL",
    "digest_value",
    "legacy_digest_value",
]
