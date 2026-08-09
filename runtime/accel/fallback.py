"""Pure Python implementations shared with the optional Cython extension."""

from __future__ import annotations

import hashlib
import json
from typing import Any


DIGEST_SCHEME = "canonical-json-blake2b-128-v1"


def legacy_digest_value(index: int, cid: Any, output: Any, error: Any) -> int:
    """Canonical result digest used by v0.8.0 and all compatibility paths."""

    payload = json.dumps(
        [index, cid, output, error],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=repr,
    ).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=16).digest(), "big")


def digest_value(index: int, cid: Any, output: Any, error: Any) -> int:
    """Avoid the general JSON encoder for the dominant integer-result case."""

    if (
        error is None
        and type(index) is int
        and type(cid) is int
        and type(output) is int
    ):
        payload = f"[{index},{cid},{output},null]".encode("ascii")
        return int.from_bytes(hashlib.blake2b(payload, digest_size=16).digest(), "big")
    return legacy_digest_value(index, cid, output, error)
