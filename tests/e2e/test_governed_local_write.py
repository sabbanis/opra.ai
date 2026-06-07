"""End-to-end governed local write test."""

from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import subprocess
import sys
import unittest

from company_os_core import AccountStage, CRMAccount, CustomerHealth
from company_os_core.serialization import write_yaml


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class GovernedLocalWriteE2ETest(unittest.TestCase):
    def test_cli_governed_write_creates_object_and_audit_event(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "input/acct_acme.yaml"
            write_yaml(
                input_path,
                CRMAccount(
                    id="acct_acme",
                    owner="ssabbani",
                    created_at=TIMESTAMP,
                    updated_at=TIMESTAMP,
                    created_by="ssabbani",
                    updated_by="ssabbani",
                    name="Acme Corp",
                    stage=AccountStage.ACTIVE_CUSTOMER,
                    industry="manufacturing",
                    arr=250000,
                    health=CustomerHealth.YELLOW,
                    renewal_date="2026-09-30",
                ),
            )

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "company_os_cli",
                    "governed-write",
                    "--file",
                    str(input_path),
                    "--repo-root",
                    str(root),
                    "--event-dir",
                    str(root / "platform/audit/events"),
                    "--user",
                    "ssabbani",
                    "--role",
                    "founder",
                    "--action",
                    "create",
                    "--request-id",
                    "req_e2e",
                ],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0)
            self.assertIn("Decision: allow", result.stdout)
            self.assertTrue((root / "modules/crm/objects/accounts/acct_acme.yaml").exists())
            self.assertEqual(len(list((root / "platform/audit/events").glob("evt_*.yaml"))), 1)


if __name__ == "__main__":
    unittest.main()
