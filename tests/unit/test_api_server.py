"""API server adapter tests."""

from pathlib import Path
import importlib.util
import tempfile
import unittest


SERVER_PATH = Path("apps/api/server.py")


def _load_server_module():
    spec = importlib.util.spec_from_file_location("company_os_api_server", SERVER_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load API server module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class APIServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = _load_server_module()

    def test_wants_html_detects_browser_accept_header(self) -> None:
        self.assertTrue(self.server._wants_html({"Accept": "text/html,application/xhtml+xml"}))
        self.assertFalse(self.server._wants_html({"Accept": "*/*"}))

    def test_static_asset_path_allows_known_assets_only(self) -> None:
        self.assertEqual(
            self.server._static_asset_path("/static/app.css"),
            self.server.WEB_STATIC_ROOT / "app.css",
        )
        self.assertIsNone(self.server._static_asset_path("/static/../server.py"))

    def test_content_type_for_static_assets(self) -> None:
        self.assertEqual(
            self.server._content_type_for(Path("app.css")),
            "text/css; charset=utf-8",
        )
        self.assertEqual(
            self.server._content_type_for(Path("app.js")),
            "application/javascript; charset=utf-8",
        )

    def test_local_identity_login_uses_seeded_uid_and_passcode(self) -> None:
        service = self._identity_service_with_users(("owner", "owner"),)

        failed = service.login(uid="owner", passcode="wrong")
        self.assertEqual(failed.status_code, 401)

        response = service.login(uid="owner", passcode="demo")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.body["user"]["uid"], "owner")
        self.assertNotIn("credential_digest", response.body["user"])

        user = service.user_from_session({"X-Opra-Session": response.body["session_id"]})
        self.assertIsNotNone(user)
        self.assertEqual(user.username, "owner")
        self.assertIn("founder", user.roles)

    def test_local_identity_registration_is_scoped_to_operator_personas(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            service = self.server.LocalIdentityService(Path(tmpdir) / "users.json")

            response = service.register(
                {
                    "uid": "new_support",
                    "passcode": "demo",
                    "display_name": "New Support",
                    "email": "new-support@example.test",
                    "persona": "support_engineer",
                }
            )
            self.assertEqual(response.status_code, 201)
            self.assertEqual(response.body["user"]["persona"], "support_engineer")
            self.assertEqual(service.login("new_support", "demo").status_code, 200)

            owner_response = service.register(
                {
                    "uid": "new_owner",
                    "passcode": "demo",
                    "display_name": "New Owner",
                    "persona": "owner",
                }
            )
            self.assertEqual(owner_response.status_code, 403)

            duplicate = service.register(
                {
                    "uid": "new_support",
                    "passcode": "demo",
                    "display_name": "Duplicate",
                    "persona": "support_engineer",
                }
            )
            self.assertEqual(duplicate.status_code, 409)

    def test_owner_or_admin_can_manage_users(self) -> None:
        service = self._identity_service_with_users(
            ("owner", "owner"),
            ("customer_operator", "customer_operator"),
        )
        owner_session = service.login("owner", "demo").body["session_id"]
        owner = service.user_from_session({"X-Opra-Session": owner_session})
        assert owner is not None

        created = service.create_user(
            owner,
            {
                "uid": "new_hiring",
                "passcode": "demo",
                "display_name": "New Hiring",
                "email": "new-hiring@example.test",
                "persona": "hiring_manager",
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.body["user"]["persona"], "hiring_manager")
        self.assertGreaterEqual(len(service.list_users(owner).body["users"]), 3)

        operator_session = service.login("customer_operator", "demo").body["session_id"]
        operator = service.user_from_session({"X-Opra-Session": operator_session})
        assert operator is not None
        self.assertEqual(service.list_users(operator).status_code, 403)
        self.assertEqual(
            service.create_user(
                operator,
                {
                    "uid": "blocked",
                    "passcode": "demo",
                    "display_name": "Blocked",
                    "persona": "support_engineer",
                },
            ).status_code,
            403,
        )

    def _identity_service_with_users(self, *seed_users):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        service = self.server.LocalIdentityService(Path(tmpdir.name) / "users.json")
        users = [
            service._build_user(
                uid=uid,
                passcode="demo",
                display_name=uid.replace("_", " ").title(),
                email=f"{uid}@example.test",
                persona=persona,
            )
            for uid, persona in seed_users
        ]
        service._write_store({"users": users})
        return service


if __name__ == "__main__":
    unittest.main()
