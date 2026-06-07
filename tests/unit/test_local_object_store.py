"""Local object store tests."""

from datetime import datetime, timezone
from tempfile import TemporaryDirectory
from pathlib import Path
import unittest

from company_os_core import BaseObject, LocalObjectStore, ObjectLink
from company_os_core.schema import base_object_schema
from company_os_core.serialization import read_yaml, stable_hash


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class LocalObjectStoreTests(unittest.TestCase):
    def test_writes_and_reads_object_from_module_path(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(
                root,
                path_map={"account": "modules/crm/objects/accounts"},
            )
            account = BaseObject(
                id="acct_acme",
                object_type="account",
                owner="ssabbani",
                created_at=TIMESTAMP,
                updated_at=TIMESTAMP,
                created_by="ssabbani",
                updated_by="ssabbani",
                links=(
                    ObjectLink(
                        target_type="opportunity",
                        target_id="opp_acme_renewal",
                        relationship="has_opportunity",
                    ),
                ),
                tags=("design_partner", "strategic"),
            )

            stored = store.write_object(account, schema=base_object_schema("account"))
            reloaded = store.read_object("account", "acct_acme")

            self.assertEqual(
                stored.path,
                root / "modules/crm/objects/accounts/acct_acme.yaml",
            )
            self.assertEqual(reloaded.data["id"], "acct_acme")
            self.assertEqual(reloaded.data["links"][0]["target_id"], "opp_acme_renewal")
            self.assertEqual(reloaded.content_hash, stable_hash(reloaded.data))

    def test_lists_object_ids(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root, path_map={"account": "modules/crm/objects/accounts"})
            for account_id in ("acct_acme", "acct_globex"):
                store.write_object(
                    BaseObject(
                        id=account_id,
                        object_type="account",
                        owner="ssabbani",
                        created_at=TIMESTAMP,
                        updated_at=TIMESTAMP,
                        created_by="ssabbani",
                        updated_by="ssabbani",
                    )
                )

            self.assertEqual(store.list_object_ids("account"), ("acct_acme", "acct_globex"))

    def test_parser_reads_yaml_written_by_serializer(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = LocalObjectStore(root)
            account = BaseObject(
                id="acct_acme",
                object_type="account",
                owner="ssabbani",
                created_at=TIMESTAMP,
                updated_at=TIMESTAMP,
                created_by="ssabbani",
                updated_by="ssabbani",
                metadata={"industry": "manufacturing"},
            )

            stored = store.write_object(account)
            data = read_yaml(stored.path)

            self.assertEqual(data["metadata"]["industry"], "manufacturing")


if __name__ == "__main__":
    unittest.main()
