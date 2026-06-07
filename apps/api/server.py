"""Local opra.ai API server."""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Mapping, Optional
from urllib.parse import parse_qs, urlparse

from company_os_core import (
    APIResponse,
    LocalReadAPI,
    Permission,
    PermissionAction,
    PolicyEngine,
    RBACEngine,
    Role,
    User,
    approval_required,
)
from company_os_core.serialization import to_json


WEB_STATIC_ROOT = Path(__file__).resolve().parents[1] / "web" / "static"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local opra.ai API server.")
    parser.add_argument("--repo-root", default=".", help="opra.ai repository root.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    api = LocalReadAPI(
        repo_root=Path(args.repo_root).resolve(),
        policy_engine=_demo_policy_engine(),
    )
    handler = _handler_for(api)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"opra.ai API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nopra.ai API stopped.")
    finally:
        server.server_close()
    return 0


def _handler_for(api: LocalReadAPI):
    class CompanyOSAPIHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/" and _wants_html(self.headers):
                self._write_file(WEB_STATIC_ROOT / "index.html", "text/html; charset=utf-8")
                return

            static_path = _static_asset_path(parsed.path)
            if static_path is not None:
                self._write_file(static_path, _content_type_for(static_path))
                return

            query = _single_value_query(parse_qs(parsed.query))
            response = api.handle_get(
                path=parsed.path,
                query=query,
                user=_user_from_headers(self.headers),
            )
            self._write_json(response)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                body = _read_json_body(self)
            except ValueError as exc:
                self._write_json(APIResponse(status_code=400, body={"error": str(exc)}))
                return

            response = api.handle_post(
                path=parsed.path,
                body=body,
                user=_user_from_headers(self.headers),
            )
            self._write_json(response)

        def log_message(self, format: str, *args) -> None:
            return

        def _write_json(self, response: APIResponse) -> None:
            payload = to_json(response.body).encode("utf-8")
            self.send_response(response.status_code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _write_file(self, path: Path, content_type: str) -> None:
            if not path.exists():
                self._write_json(APIResponse(status_code=404, body={"error": "Asset not found."}))
                return

            payload = path.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    return CompanyOSAPIHandler


def _read_json_body(handler: BaseHTTPRequestHandler) -> Mapping[str, object]:
    raw_length = handler.headers.get("Content-Length", "0")
    try:
        length = int(raw_length)
    except ValueError as exc:
        raise ValueError("Invalid Content-Length header.") from exc
    if length <= 0:
        return {}
    if length > 1_000_000:
        raise ValueError("Request body is too large.")

    payload = handler.rfile.read(length).decode("utf-8")
    try:
        body = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise ValueError("Request body must be valid JSON.") from exc
    if not isinstance(body, Mapping):
        raise ValueError("Request body must be a JSON object.")
    return body


def _wants_html(headers) -> bool:
    return "text/html" in headers.get("Accept", "")


def _static_asset_path(path: str) -> Optional[Path]:
    assets = {
        "/static/app.css": WEB_STATIC_ROOT / "app.css",
        "/static/app.js": WEB_STATIC_ROOT / "app.js",
    }
    return assets.get(path)


def _content_type_for(path: Path) -> str:
    if path.suffix == ".css":
        return "text/css; charset=utf-8"
    if path.suffix == ".js":
        return "application/javascript; charset=utf-8"
    return "application/octet-stream"


def _single_value_query(values: Mapping[str, list[str]]) -> Mapping[str, str]:
    return {key: items[-1] for key, items in values.items() if items}


def _user_from_headers(headers) -> User:
    username = headers.get("X-Opra-User", "") or headers.get("X-Company-OS-User", "")
    roles = tuple(
        role.strip()
        for role in (
            headers.get("X-Opra-Roles", "") or headers.get("X-Company-OS-Roles", "")
        ).split(",")
        if role.strip()
    )
    return User(id=username or "anonymous", username=username or "anonymous", roles=roles)


def _demo_policy_engine() -> PolicyEngine:
    sales_rep = Role(
        id="sales_rep",
        name="Sales Rep",
        permissions=(
            Permission(
                subject="sales_rep",
                action=PermissionAction.READ,
                object_type="account",
                scope="company",
            ),
            Permission(
                subject="sales_rep",
                action=PermissionAction.READ,
                object_type="opportunity",
                scope="company",
            ),
            Permission(
                subject="sales_rep",
                action=PermissionAction.UPDATE,
                object_type="account",
                scope="owned_by_me",
                fields=("status", "tags", "metadata"),
            ),
        ),
    )
    sales_manager = Role(
        id="sales_manager",
        name="Sales Manager",
        permissions=(
            Permission(
                subject="sales_manager",
                action=PermissionAction.READ,
                object_type="account",
                scope="company",
            ),
            Permission(
                subject="sales_manager",
                action=PermissionAction.READ,
                object_type="opportunity",
                scope="company",
            ),
            Permission(
                subject="sales_manager",
                action=PermissionAction.APPROVE,
                object_type="account",
                scope="company",
            ),
        ),
    )
    founder = Role(
        id="founder",
        name="Founder",
        permissions=(
            Permission(
                subject="founder",
                action=PermissionAction.ALL,
                object_type="*",
                scope="company",
            ),
        ),
    )
    return PolicyEngine(
        rbac=RBACEngine(roles=(founder, sales_rep, sales_manager)),
        approval_rules=(
            approval_required(
                object_type="account",
                action=PermissionAction.UPDATE,
                fields=("metadata",),
                required_approvers=("sales_manager",),
                reason="Account metadata changes require sales manager approval in demo policy.",
                rule_id="account_metadata_approval",
            ),
        ),
    )


if __name__ == "__main__":
    raise SystemExit(main())
