from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Mapping


@dataclass(frozen=True, slots=True)
class SandboxPolicy:
    """Declarative policy shared by Python and the future native launcher.

    Changing cwd and environment variables is not a security boundary.  The
    ``native_enforced`` flag must remain false until the Windows restricted
    token, Job Object and directory ACL have all been applied successfully.
    """

    workspace: Path
    memory_limit_bytes: int = 512 * 1024 * 1024
    process_limit: int = 1
    allow_network: bool = False
    allowed_environment: tuple[str, ...] = (
        "PATH",
        "PYTHONPATH",
        "SYSTEMROOT",
        "WINDIR",
        "TEMP",
        "TMP",
    )
    extra_environment: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        workspace = self.workspace.resolve()
        if not workspace.is_dir():
            raise ValueError(f"sandbox workspace does not exist: {workspace}")
        if self.memory_limit_bytes <= 0 or self.process_limit <= 0:
            raise ValueError("sandbox limits must be positive")
        object.__setattr__(self, "workspace", workspace)

    def child_environment(self) -> dict[str, str]:
        environment = {
            key: value
            for key, value in os.environ.items()
            if key.upper() in self.allowed_environment
        }
        environment.update(self.extra_environment)
        environment["OJ_SANDBOX_WORKSPACE"] = str(self.workspace)
        environment["OJ_SANDBOX_NETWORK"] = "1" if self.allow_network else "0"
        return environment

    @property
    def native_enforced(self) -> bool:
        return False
