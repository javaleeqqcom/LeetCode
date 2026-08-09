from __future__ import annotations

import re
import unittest
from pathlib import Path

from runtime import __version__


ROOT = Path(__file__).resolve().parent.parent


class VersionTests(unittest.TestCase):
    def test_runtime_readme_and_project_metadata_are_synchronized(self) -> None:
        project_file = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        project_match = re.search(
            r'^version\s*=\s*"([^"]+)"$', project_file, re.MULTILINE
        )
        readme_match = re.search(r"^- 版本：([^\s]+)$", readme, re.MULTILINE)
        self.assertIsNotNone(project_match)
        self.assertIsNotNone(readme_match)
        self.assertEqual(project_match.group(1), __version__)
        self.assertEqual(readme_match.group(1), __version__)


if __name__ == "__main__":
    unittest.main(verbosity=2)
