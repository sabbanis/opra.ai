# API App

Local API application. The API should expose platform core behavior without owning core business logic.

## Local Server

The API surface is dependency-free and local-first. It exposes CRM dashboard reads, module summaries, source-record validation, governed CRUD actions, proposal workflow actions, GitHub preview actions, PR-backed message previews, CRUD Skill descriptors, and audit evidence through the same core services used by the CLI.

Run it locally:

```bash
PYTHONPATH=packages/company_os_core/src python3 apps/api/server.py --repo-root . --port 8080
```

Example requests:

```bash
curl http://127.0.0.1:8080/
SESSION_ID=$(
  curl -fsS \
    -X POST \
    -H "Content-Type: application/json" \
    -d '{"uid":"owner","passcode":"demo"}' \
    http://127.0.0.1:8080/auth/login \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["session_id"])'
)
curl -H "X-Opra-Session: $SESSION_ID" http://127.0.0.1:8080/auth/me
curl -H "X-Opra-Session: $SESSION_ID" http://127.0.0.1:8080/crm/summary
curl -H "X-Opra-Session: $SESSION_ID" http://127.0.0.1:8080/users
curl -H "X-Opra-Session: $SESSION_ID" http://127.0.0.1:8080/github/messages
```

Opening `http://127.0.0.1:8080/` in a browser serves the local workspace for sign-in, registration, Customers, Delivery, People, governed work changes, approvals, PR-backed messages, publishing drafts, activity, and owner/admin user management.
