"""API server adapter tests."""

from pathlib import Path
import importlib.util
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


if __name__ == "__main__":
    unittest.main()
