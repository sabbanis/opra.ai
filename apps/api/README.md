# API App

Local API application. The API should expose platform core behavior without owning core business logic.

## Local Server

The API surface is dependency-free and local-first. It exposes CRM dashboard reads, module summaries, source-record validation, governed writes, proposal workflow actions, GitHub preview actions, and audit evidence through the same core services used by the CLI.

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

Opening `http://127.0.0.1:8080/` in a browser serves the local workspace for CRM, Issues, HR, records, proposals, GitHub previews, and audit.
