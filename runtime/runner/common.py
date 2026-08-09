from __future__ import annotations

import hashlib
import io
import json
from typing import Any


class BoundedWriter(io.TextIOBase):
    def __init__(self, limit: int = 64 * 1024) -> None:
        self.limit = limit
        self.size = 0
        self.parts: list[str] = []
        self.truncated = False

    def writable(self) -> bool:
        return True

    def write(self, text: str) -> int:
        original_length = len(text)
        remaining = self.limit - self.size
        if remaining > 0:
            piece = text[:remaining]
            self.parts.append(piece)
            self.size += len(piece)
        if original_length > max(remaining, 0):
            self.truncated = True
        return original_length

    def getvalue(self) -> str:
        value = "".join(self.parts)
        if self.truncated:
            value += "\n... <stdout truncated>"
        return value


def digest_value(index: int, cid: Any, output: Any, error: Any) -> int:
    payload = json.dumps(
        [index, cid, output, error],
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=repr,
    ).encode("utf-8")
    return int.from_bytes(hashlib.blake2b(payload, digest_size=16).digest(), "big")
