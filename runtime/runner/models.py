from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from runtime.accel import DIGEST_SCHEME


@dataclass
class RunMetrics:
    backend: str
    workers: int
    case_count: int
    wall_seconds: float
    throughput_cases_per_second: float
    pool_startup_seconds: float
    worker_compute_seconds: float
    worker_decode_seconds: float
    peak_worker_rss_bytes: int
    worker_restarts: int = 0
    timed_out_cases: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RunReport:
    metrics: RunMetrics
    correct_count: int
    wrong_count: int
    error_count: int
    digest: str
    digest_scheme: str = DIGEST_SCHEME
    results: list[dict[str, Any]] | None = field(default=None)

    @property
    def completed_count(self) -> int:
        return self.correct_count + self.wrong_count + self.error_count

    def to_dict(self, include_results: bool = False) -> dict[str, Any]:
        payload = {
            "metrics": self.metrics.to_dict(),
            "correct_count": self.correct_count,
            "wrong_count": self.wrong_count,
            "error_count": self.error_count,
            "digest": self.digest,
            "digest_scheme": self.digest_scheme,
        }
        if include_results:
            payload["results"] = self.results
        return payload
