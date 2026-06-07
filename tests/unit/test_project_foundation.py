"""Milestone 0 repository foundation tests."""

from pathlib import Path
import subprocess
import sys
import unittest

from company_os_core import PRODUCT_NAME, __version__
from company_os_core.project import REQUIRED_TOP_LEVEL_PATHS, missing_required_paths


REPO_ROOT = Path(__file__).resolve().parents[2]


class ProjectFoundationTests(unittest.TestCase):
    def test_package_metadata(self) -> None:
        self.assertEqual(PRODUCT_NAME, "opra.ai")
        self.assertEqual(__version__, "0.1.0")

    def test_required_top_level_paths_exist(self) -> None:
        self.assertEqual(missing_required_paths(REPO_ROOT), ())

    def test_required_path_contract_mentions_expected_dirs(self) -> None:
        self.assertIn("modules", REQUIRED_TOP_LEVEL_PATHS)
        self.assertIn("platform", REQUIRED_TOP_LEVEL_PATHS)
        self.assertIn("apps", REQUIRED_TOP_LEVEL_PATHS)
        self.assertIn("packages", REQUIRED_TOP_LEVEL_PATHS)

    def test_cli_doctor_passes_for_repo_root(self) -> None:
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "company_os_cli",
                "doctor",
                "--repo-root",
                str(REPO_ROOT),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(result.returncode, 0)
        self.assertIn("opra.ai repository check passed.", result.stdout)


if __name__ == "__main__":
    unittest.main()
