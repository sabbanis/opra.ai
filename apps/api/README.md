# API App

Local API application. The API should expose platform core behavior without owning core business logic.

## Local Server

The first API surface is dependency-free and read-only. It exposes CRM dashboard and Skill-style read endpoints through the same core read model and policy checks used by the CLI.

Run it locally:

```bash
PYTHONPATH=packages/company_os_core/src python3 apps/api/server.py --repo-root . --port 8080
```

Example requests:

```bash
curl http://127.0.0.1:8080/
curl -H "X-Company-OS-User: ssabbani" -H "X-Company-OS-Roles: sales_rep" http://127.0.0.1:8080/crm/summary
curl -H "X-Company-OS-User: ssabbani" -H "X-Company-OS-Roles: sales_rep" http://127.0.0.1:8080/crm/skills/pipeline-summary
```

Opening `http://127.0.0.1:8080/` in a browser serves the local CRM dashboard.
