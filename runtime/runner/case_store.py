from __future__ import annotations

import json
import mmap
import os
import shutil
import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping

from .common import digest_value


MAGIC = b"OJBIN001"
VERSION = 2
HEADER = struct.Struct("<8sIQQQ")
INDEX_ENTRY_V1 = struct.Struct("<QQ")
INDEX_ENTRY = struct.Struct("<QQ16sB7x")
FLAG_EXPECTED_DIGEST = 1


@dataclass(frozen=True)
class CaseStoreInfo:
    path: Path
    case_count: int
    file_size: int
    table_offset: int
    format_version: int = VERSION


def _normalize_case(raw_case: Mapping[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(raw_case, Mapping):
        raise TypeError(f"case {index} must be a mapping")
    if "input" not in raw_case:
        raise ValueError(f"case {index} is missing 'input'")
    case = dict(raw_case)
    case.setdefault("cid", index)
    if not isinstance(case["cid"], (str, int)):
        raise TypeError(f"case {index} cid must be str or int")
    if not isinstance(case["input"], (list, tuple, dict)):
        raise TypeError(f"case {index} input must be list, tuple or dict")
    return case


class CaseStoreWriter:
    """Write JSON-compatible cases to a versioned, mmap-friendly file.

    The offset table is stored at the end of the file.  A temporary index file
    keeps memory usage bounded even when writing one million cases.
    """

    @classmethod
    def write(
        cls,
        path: os.PathLike[str] | str,
        cases: Iterable[Mapping[str, Any]],
    ) -> CaseStoreInfo:
        destination = Path(path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        data_temp = destination.with_name(destination.name + ".writing")
        index_temp_handle = tempfile.NamedTemporaryFile(
            mode="w+b", prefix="ojbin_index_", dir=destination.parent, delete=False
        )
        index_temp = Path(index_temp_handle.name)
        count = 0
        try:
            with data_temp.open("w+b") as data_handle, index_temp_handle as index_handle:
                data_handle.write(b"\x00" * HEADER.size)
                payload_start = data_handle.tell()
                for index, raw_case in enumerate(cases):
                    case = _normalize_case(raw_case, index)
                    payload = json.dumps(
                        case,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    ).encode("utf-8")
                    offset = data_handle.tell()
                    data_handle.write(payload)
                    flags = 0
                    expected_digest = b"\x00" * 16
                    if "expected" in case:
                        flags |= FLAG_EXPECTED_DIGEST
                        expected_digest = digest_value(
                            index,
                            case["cid"],
                            case["expected"],
                            None,
                        ).to_bytes(16, "big")
                    index_handle.write(
                        INDEX_ENTRY.pack(offset, len(payload), expected_digest, flags)
                    )
                    count += 1

                table_offset = data_handle.tell()
                index_handle.flush()
                index_handle.seek(0)
                shutil.copyfileobj(index_handle, data_handle, length=1024 * 1024)
                data_handle.seek(0)
                data_handle.write(
                    HEADER.pack(MAGIC, VERSION, count, table_offset, payload_start)
                )
                data_handle.flush()
                os.fsync(data_handle.fileno())
            os.replace(data_temp, destination)
        finally:
            index_temp.unlink(missing_ok=True)
            data_temp.unlink(missing_ok=True)

        return CaseStoreInfo(
            path=destination,
            case_count=count,
            file_size=destination.stat().st_size,
            table_offset=table_offset,
        )


class CaseStoreReader:
    def __init__(self, path: os.PathLike[str] | str) -> None:
        self.path = Path(path).resolve()
        self._handle = self.path.open("rb")
        try:
            self._map = mmap.mmap(self._handle.fileno(), length=0, access=mmap.ACCESS_READ)
            if self._map.size() < HEADER.size:
                raise ValueError(f"case store is truncated: {self.path}")
            magic, version, count, table_offset, payload_start = HEADER.unpack_from(
                self._map, 0
            )
            if magic != MAGIC:
                raise ValueError(f"invalid case-store magic: {magic!r}")
            if version not in {1, VERSION}:
                raise ValueError(f"unsupported case-store version: {version}")
            self.format_version = version
            self._index_entry = INDEX_ENTRY if version == VERSION else INDEX_ENTRY_V1
            expected_size = table_offset + count * self._index_entry.size
            if payload_start != HEADER.size or expected_size > self._map.size():
                raise ValueError(f"invalid case-store offsets: {self.path}")
            self.case_count = count
            self.table_offset = table_offset
        except Exception:
            self._handle.close()
            raise

    def __len__(self) -> int:
        return self.case_count

    def _record_metadata(self, index: int) -> tuple[int, int, int | None]:
        if index < 0:
            index += self.case_count
        if index < 0 or index >= self.case_count:
            raise IndexError(index)
        entry_offset = self.table_offset + index * self._index_entry.size
        expected_digest: int | None = None
        if self.format_version == VERSION:
            offset, length, digest_bytes, flags = INDEX_ENTRY.unpack_from(
                self._map, entry_offset
            )
            if flags & FLAG_EXPECTED_DIGEST:
                expected_digest = int.from_bytes(digest_bytes, "big")
        else:
            offset, length = INDEX_ENTRY_V1.unpack_from(self._map, entry_offset)
        end = offset + length
        if offset < HEADER.size or end > self.table_offset:
            raise ValueError(f"case {index} points outside payload section")
        return offset, end, expected_digest

    def _record_bounds(self, index: int) -> tuple[int, int]:
        offset, end, _ = self._record_metadata(index)
        return offset, end

    def read_record(self, index: int) -> tuple[dict[str, Any], int | None]:
        """Decode one case and return its precomputed expected-result digest."""

        offset, end, expected_digest = self._record_metadata(index)
        case = json.loads(self._map[offset:end])
        if isinstance(case.get("input"), list):
            case["input"] = tuple(case["input"])
        return case, expected_digest

    def __getitem__(self, index: int) -> dict[str, Any]:
        case, _ = self.read_record(index)
        return case

    def iter_range(self, start: int = 0, stop: int | None = None) -> Iterator[dict[str, Any]]:
        upper = self.case_count if stop is None else min(stop, self.case_count)
        for index in range(max(0, start), upper):
            yield self[index]

    def close(self) -> None:
        if getattr(self, "_map", None) is not None:
            self._map.close()
            self._map = None
        if getattr(self, "_handle", None) is not None:
            self._handle.close()
            self._handle = None

    def __enter__(self) -> "CaseStoreReader":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
