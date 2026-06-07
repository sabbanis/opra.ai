# First CRM Demo

## Purpose

This demo shows the free local CRM path: validate source records, build a read model, run a Skill, and view the local dashboard.

## Setup

```bash
cd opra.ai
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
```

## Validate CRM Records

```bash
python3 -m company_os_cli validate --file modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli validate --file modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml
```

Expected:

```text
Validation passed
```

## Inspect An Account

```bash
python3 -m company_os_cli inspect --file modules/crm/objects/accounts/acct_acme.yaml
```

Expected:

- JSON output.
- `id` is `acct_acme`.
- `object_type` is `account`.

## Build The CRM Read Model

```bash
python3 -m company_os_cli index-crm
```

Expected:

- Read model is written to `platform/dashboards/read_models/crm_summary.json`.
- Output includes account and opportunity counts.

## Run A CRM Skill

```bash
python3 -m company_os_cli crm-skill \
  --name pipeline-summary \
  --user ssabbani \
  --role sales_rep
```

Expected:

- Decision is `allow`.
- Summary includes open pipeline.

## Open The Browser Dashboard

```bash
python3 apps/api/server.py --repo-root . --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

Expected:

- The local CRM dashboard loads.
- The account and opportunity seed data are visible.

Stop the server with `Ctrl+C`.
