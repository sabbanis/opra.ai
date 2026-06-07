"""Checks that the public repo does not leak internal working context."""

from __future__ import annotations

import unittest
from pathlib import Path

from tools.public_repo_hygiene import scan_repo


REPO_ROOT = Path(__file__).resolve().parents[2]


class PublicRepoHygieneTests(unittest.TestCase):
    def test_public_repo_has_no_internal_info(self) -> None:
        findings = scan_repo(REPO_ROOT)
        if findings:
            formatted = "\n".join(finding.format() for finding in findings)
            self.fail(f"Public repository hygiene findings:\n{formatted}")


if __name__ == "__main__":
    unittest.main()
