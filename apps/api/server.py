"""Local opra.ai API server."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import secrets
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Optional
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
DEFAULT_USER_STORE = Path("platform/identity/users.json")
ADMIN_PERSONAS = {"owner", "company_os_admin"}
SELF_REGISTER_PERSONAS = {
    "customer_operator",
    "support_engineer",
    "hiring_manager",
}
PERSONA_DEFS: Mapping[str, Mapping[str, Any]] = {
    "owner": {
        "roles": ("founder",),
        "modules": ("crm", "issues", "hr"),
    },
    "company_os_admin": {
        "roles": ("company_os_admin",),
        "modules": ("crm", "issues", "hr"),
    },
    "customer_lead": {
        "roles": ("customer_lead", "sales_manager"),
        "modules": ("crm",),
    },
    "customer_operator": {
        "roles": ("customer_operator", "sales_rep"),
        "modules": ("crm",),
    },
    "engineering_lead": {
        "roles": ("engineering_lead",),
        "modules": ("issues",),
    },
    "support_engineer": {
        "roles": ("support_engineer",),
        "modules": ("issues",),
    },
    "people_ops": {
        "roles": ("people_ops",),
        "modules": ("hr",),
    },
    "hiring_manager": {
        "roles": ("hiring_manager",),
        "modules": ("hr",),
    },
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local opra.ai API server.")
    parser.add_argument("--repo-root", default=".", help="opra.ai repository root.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind.")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    repo_root = Path(args.repo_root).resolve()
    api = LocalReadAPI(
        repo_root=repo_root,
        policy_engine=_demo_policy_engine(),
    )
    identity_service = LocalIdentityService(repo_root / DEFAULT_USER_STORE)
    handler = _handler_for(api, identity_service)
    server = ThreadingHTTPServer((args.host, args.port), handler)
    print(f"opra.ai API listening on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nopra.ai API stopped.")
    finally:
        server.server_close()
    return 0


class LocalIdentityService:
    """Local demo identity store for browser sign-in and user administration."""

    def __init__(self, user_store: Path) -> None:
        self._user_store = user_store
        self._sessions: dict[str, str] = {}
        self._ensure_store()

    def login(self, uid: str, passcode: str) -> APIResponse:
        user = self._user_by_uid(uid)
        if user is None or user.get("state") != "active":
            return APIResponse(status_code=401, body={"error": "Invalid sign-in."})
        expected = str(user.get("credential_digest", ""))
        actual = self._credential_digest(uid=uid, passcode=passcode)
        if not hmac.compare_digest(expected, actual):
            return APIResponse(status_code=401, body={"error": "Invalid sign-in."})

        session_id = secrets.token_urlsafe(32)
        self._sessions[session_id] = str(user["id"])
        return APIResponse(
            status_code=200,
            body={
                "session_id": session_id,
                "user": self._public_user(user),
            },
        )

    def register(self, body: Mapping[str, object]) -> APIResponse:
        uid = _required_text("uid", str(body.get("uid", "")))
        passcode = _required_text("passcode", str(body.get("passcode", "")))
        display_name = _required_text("display_name", str(body.get("display_name", "")))
        email = str(body.get("email", "")).strip()
        persona = str(body.get("persona", "customer_operator")).strip() or "customer_operator"
        if persona not in SELF_REGISTER_PERSONAS:
            return APIResponse(status_code=403, body={"error": "That persona must be assigned by an admin."})
        if self._user_by_uid(uid) is not None:
            return APIResponse(status_code=409, body={"error": "UID already exists."})

        user = self._build_user(
            uid=uid,
            passcode=passcode,
            display_name=display_name,
            email=email,
            persona=persona,
        )
        data = self._read_store()
        users = list(data.get("users", []))
        users.append(user)
        self._write_store({"users": users})
        return APIResponse(status_code=201, body={"user": self._public_user(user)})

    def list_users(self, actor: User) -> APIResponse:
        if not self._can_manage_users(actor):
            return APIResponse(status_code=403, body={"error": "User management requires owner or admin."})
        return APIResponse(
            status_code=200,
            body={"users": [self._public_user(user) for user in self._users()]},
        )

    def create_user(self, actor: User, body: Mapping[str, object]) -> APIResponse:
        if not self._can_manage_users(actor):
            return APIResponse(status_code=403, body={"error": "User management requires owner or admin."})
        uid = _required_text("uid", str(body.get("uid", "")))
        passcode = _required_text("passcode", str(body.get("passcode", "")))
        display_name = _required_text("display_name", str(body.get("display_name", "")))
        email = str(body.get("email", "")).strip()
        persona = _required_text("persona", str(body.get("persona", "")))
        if persona not in PERSONA_DEFS:
            return APIResponse(status_code=422, body={"error": f"Unknown persona: {persona}"})
        if self._user_by_uid(uid) is not None:
            return APIResponse(status_code=409, body={"error": "UID already exists."})

        user = self._build_user(
            uid=uid,
            passcode=passcode,
            display_name=display_name,
            email=email,
            persona=persona,
        )
        data = self._read_store()
        users = list(data.get("users", []))
        users.append(user)
        self._write_store({"users": users})
        return APIResponse(status_code=201, body={"user": self._public_user(user)})

    def user_from_session(self, headers) -> Optional[User]:
        session_id = headers.get("X-Opra-Session", "")
        user_id = self._sessions.get(session_id)
        if not user_id:
            return None
        user = self._user_by_id(user_id)
        if user is None or user.get("state") != "active":
            return None
        return self._api_user(user)

    def user_from_session_payload(self, headers) -> APIResponse:
        user = self.user_from_session(headers)
        if user is None:
            return APIResponse(status_code=401, body={"error": "Sign-in required."})
        stored = self._user_by_id(user.id)
        if stored is None:
            return APIResponse(status_code=401, body={"error": "Sign-in required."})
        return APIResponse(status_code=200, body={"user": self._public_user(stored)})

    def logout(self, headers) -> APIResponse:
        session_id = headers.get("X-Opra-Session", "")
        if session_id:
            self._sessions.pop(session_id, None)
        return APIResponse(status_code=200, body={"status": "signed_out"})

    def _ensure_store(self) -> None:
        if self._user_store.exists():
            return
        self._user_store.parent.mkdir(parents=True, exist_ok=True)
        self._write_store({"users": []})

    def _read_store(self) -> Mapping[str, Any]:
        return json.loads(self._user_store.read_text(encoding="utf-8"))

    def _write_store(self, data: Mapping[str, Any]) -> None:
        self._user_store.parent.mkdir(parents=True, exist_ok=True)
        self._user_store.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _users(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self._read_store().get("users", []))

    def _user_by_uid(self, uid: str) -> Optional[Mapping[str, Any]]:
        normalized = uid.strip()
        for user in self._users():
            if str(user.get("uid", "")) == normalized:
                return user
        return None

    def _user_by_id(self, user_id: str) -> Optional[Mapping[str, Any]]:
        for user in self._users():
            if str(user.get("id", "")) == user_id:
                return user
        return None

    def _build_user(
        self,
        uid: str,
        passcode: str,
        display_name: str,
        email: str,
        persona: str,
    ) -> Mapping[str, Any]:
        persona_def = PERSONA_DEFS[persona]
        return {
            "id": f"usr_{uuid.uuid4().hex[:12]}",
            "uid": uid.strip(),
            "display_name": display_name.strip(),
            "email": email,
            "persona": persona,
            "roles": list(persona_def["roles"]),
            "modules": list(persona_def["modules"]),
            "state": "active",
            "credential_digest": self._credential_digest(uid=uid.strip(), passcode=passcode),
        }

    def _public_user(self, user: Mapping[str, Any]) -> Mapping[str, Any]:
        return {
            key: value
            for key, value in user.items()
            if key != "credential_digest"
        }

    def _api_user(self, user: Mapping[str, Any]) -> User:
        return User(
            id=str(user.get("id", "")),
            username=str(user.get("uid", "")),
            email=str(user.get("email", "")),
            display_name=str(user.get("display_name", "")),
            roles=tuple(str(role) for role in user.get("roles", [])),
        )

    def _credential_digest(self, uid: str, passcode: str) -> str:
        return hashlib.sha256(f"{uid}:{passcode}".encode("utf-8")).hexdigest()

    def _can_manage_users(self, actor: User) -> bool:
        return bool(set(actor.roles) & {"founder", "company_os_admin"})


def _handler_for(api: LocalReadAPI, identity_service: LocalIdentityService):
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

            if parsed.path == "/auth/me":
                self._write_json(identity_service.user_from_session_payload(self.headers))
                return
            if parsed.path == "/users":
                user = self._signed_in_user()
                if user is None:
                    return
                self._write_json(identity_service.list_users(user))
                return

            query = _single_value_query(parse_qs(parsed.query))
            user = identity_service.user_from_session(self.headers)
            if user is None and parsed.path not in ("/", "/health"):
                self._write_json(APIResponse(status_code=401, body={"error": "Sign-in required."}))
                return
            response = api.handle_get(
                path=parsed.path,
                query=query,
                user=user or _anonymous_user(),
            )
            self._write_json(response)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            try:
                body = _read_json_body(self)
            except ValueError as exc:
                self._write_json(APIResponse(status_code=400, body={"error": str(exc)}))
                return

            if parsed.path == "/auth/login":
                self._write_json(
                    identity_service.login(
                        uid=str(body.get("uid", "")),
                        passcode=str(body.get("passcode", "")),
                    )
                )
                return
            if parsed.path == "/auth/register":
                try:
                    response = identity_service.register(body)
                except ValueError as exc:
                    response = APIResponse(status_code=422, body={"error": str(exc)})
                self._write_json(response)
                return
            if parsed.path == "/auth/logout":
                self._write_json(identity_service.logout(self.headers))
                return
            if parsed.path == "/users":
                user = self._signed_in_user()
                if user is None:
                    return
                try:
                    response = identity_service.create_user(user, body)
                except ValueError as exc:
                    response = APIResponse(status_code=422, body={"error": str(exc)})
                self._write_json(response)
                return

            user = self._signed_in_user()
            if user is None:
                return
            response = api.handle_post(
                path=parsed.path,
                body=body,
                user=user,
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

        def _signed_in_user(self) -> Optional[User]:
            user = identity_service.user_from_session(self.headers)
            if user is None:
                self._write_json(APIResponse(status_code=401, body={"error": "Sign-in required."}))
                return None
            return user

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


def _required_text(name: str, value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError(f"{name} is required.")
    return text


def _anonymous_user() -> User:
    return User(id="anonymous", username="anonymous")


def _demo_policy_engine() -> PolicyEngine:
    all_objects = ("*",)
    crm_objects = ("account", "opportunity")
    delivery_objects = ("component", "defect", "feature_request", "incident", "rca", "release")
    people_objects = ("candidate", "employee", "interview", "job", "offer", "onboarding", "policy_ack", "time_off")
    hiring_objects = ("candidate", "interview", "job", "offer", "onboarding")

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
    customer_operator = Role(
        id="customer_operator",
        name="Customer Operator",
        permissions=tuple(
            Permission(
                subject="customer_operator",
                action=PermissionAction.ALL,
                object_type=object_type,
                scope="company",
            )
            for object_type in crm_objects
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
    customer_lead = Role(
        id="customer_lead",
        name="Customer Lead",
        permissions=tuple(
            Permission(
                subject="customer_lead",
                action=PermissionAction.ALL,
                object_type=object_type,
                scope="company",
            )
            for object_type in crm_objects
        ),
    )
    company_os_admin = Role(
        id="company_os_admin",
        name="Company OS Admin",
        permissions=tuple(
            Permission(
                subject="company_os_admin",
                action=PermissionAction.ALL,
                object_type=object_type,
                scope="company",
            )
            for object_type in all_objects
        ),
    )
    engineering_lead = Role(
        id="engineering_lead",
        name="Engineering Lead",
        permissions=tuple(
            Permission(
                subject="engineering_lead",
                action=PermissionAction.ALL,
                object_type=object_type,
                scope="company",
            )
            for object_type in delivery_objects
        ),
    )
    support_engineer = Role(
        id="support_engineer",
        name="Support Engineer",
        permissions=tuple(
            Permission(
                subject="support_engineer",
                action=PermissionAction.ALL,
                object_type=object_type,
                scope="company",
            )
            for object_type in ("defect", "incident", "rca", "component")
        ),
    )
    people_ops = Role(
        id="people_ops",
        name="People Ops",
        permissions=tuple(
            Permission(
                subject="people_ops",
                action=PermissionAction.ALL,
                object_type=object_type,
                scope="company",
            )
            for object_type in people_objects
        ),
    )
    hiring_manager = Role(
        id="hiring_manager",
        name="Hiring Manager",
        permissions=tuple(
            Permission(
                subject="hiring_manager",
                action=PermissionAction.ALL,
                object_type=object_type,
                scope="company",
            )
            for object_type in hiring_objects
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
        rbac=RBACEngine(
            roles=(
                founder,
                company_os_admin,
                customer_lead,
                customer_operator,
                sales_rep,
                sales_manager,
                engineering_lead,
                support_engineer,
                people_ops,
                hiring_manager,
            )
        ),
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
