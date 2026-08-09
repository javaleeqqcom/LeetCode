from __future__ import annotations

import io
import math
from typing import Any

from runtime.accel import DIGEST_BACKEND, DIGEST_SCHEME, digest_value


def can_reuse_expected_digest(expected: Any, output: Any) -> bool:
    """Return whether two values have the same canonical JSON representation.

    Judge equality can intentionally be looser than digest equality (for
    example, ``1 == 1.0`` and the legacy runner uses tolerant float
    comparison).  The precomputed expected digest is therefore safe only when
    every JSON value and type is exactly equivalent.
    """

    value_type = type(expected)
    if value_type is not type(output):
        return False
    if (
        value_type is type(None)
        or value_type is bool
        or value_type is int
        or value_type is str
    ):
        return expected == output
    if value_type is float:
        return expected == output and math.copysign(1.0, expected) == math.copysign(
            1.0, output
        )
    if value_type is list:
        return len(expected) == len(output) and all(
            can_reuse_expected_digest(left, right)
            for left, right in zip(expected, output)
        )
    if value_type is dict:
        if len(expected) != len(output):
            return False
        if not all(type(key) is str for key in expected):
            return False
        if not all(type(key) is str for key in output):
            return False
        return expected.keys() == output.keys() and all(
            can_reuse_expected_digest(expected[key], output[key]) for key in expected
        )
    return False


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
