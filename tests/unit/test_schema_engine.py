"""Schema engine tests."""

from datetime import datetime, timezone
import unittest

from company_os_core import BaseObject, ObjectVisibility
from company_os_core.schema import base_object_schema, validate_object
from company_os_core.serialization import to_plain_data


TIMESTAMP = datetime(2026, 6, 6, 10, 0, 0, tzinfo=timezone.utc)


class SchemaEngineTests(unittest.TestCase):
    def test_valid_base_object_passes_schema_validation(self) -> None:
        account = BaseObject(
            id="acct_acme",
            object_type="account",
            owner="ssabbani",
            visibility=ObjectVisibility.COMPANY,
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
            tags=("design_partner",),
        )

        result = validate_object(to_plain_data(account), base_object_schema("account"))

        self.assertTrue(result.valid)
        self.assertEqual(result.issues, ())

    def test_missing_required_field_fails_schema_validation(self) -> None:
        account = BaseObject(
            id="acct_acme",
            object_type="account",
            owner="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
        )
        data = to_plain_data(account)
        del data["owner"]

        result = validate_object(data, base_object_schema("account"))

        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].field, "owner")
        self.assertEqual(result.issues[0].message, "field is required")

    def test_invalid_enum_value_fails_schema_validation(self) -> None:
        account = BaseObject(
            id="acct_acme",
            object_type="account",
            owner="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
        )
        data = to_plain_data(account)
        data["status"] = "unknown"

        result = validate_object(data, base_object_schema("account"))

        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].field, "status")
        self.assertIn("must be one of", result.issues[0].message)

    def test_extra_field_fails_schema_validation_by_default(self) -> None:
        account = BaseObject(
            id="acct_acme",
            object_type="account",
            owner="ssabbani",
            created_at=TIMESTAMP,
            updated_at=TIMESTAMP,
            created_by="ssabbani",
            updated_by="ssabbani",
        )
        data = to_plain_data(account)
        data["unexpected"] = "value"

        result = validate_object(data, base_object_schema("account"))

        self.assertFalse(result.valid)
        self.assertEqual(result.issues[0].field, "unexpected")
        self.assertEqual(result.issues[0].message, "field is not allowed by schema")


if __name__ == "__main__":
    unittest.main()
