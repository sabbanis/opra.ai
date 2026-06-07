# CRM Module

Git-native CRM module for accounts, contacts, opportunities, activities, tasks, approvals, commitments, renewals, and customer health.

## Current Scope

The first CRM slice models accounts and opportunities as governed opra.ai source-of-truth objects.

Implemented objects:

- `account`
- `opportunity`

Implemented schema artifacts:

- `modules/crm/schemas/account.schema.yaml`
- `modules/crm/schemas/opportunity.schema.yaml`

Implemented workflow artifacts:

- `modules/crm/workflows/lifecycle.yaml`

Implemented Skill artifacts:

- `modules/crm/skills/README.md`

Seed records:

- `modules/crm/objects/accounts/acct_acme.yaml`
- `modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml`

## Local Validation

```bash
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m company_os_cli validate --file modules/crm/objects/accounts/acct_acme.yaml
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m company_os_cli validate --file modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml
```

Governed CRM updates also validate lifecycle transitions. For example, an account can move from `active_customer` to `renewal_due`, but not back to `lead`.

## Dashboard Read Model

```bash
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m company_os_cli index-crm
```

The generated JSON artifact is written to `platform/dashboards/read_models/crm_summary.json`.

## Skills

```bash
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m company_os_cli crm-skill --name pipeline-summary --user ssabbani --role sales_rep
```
