# CRM Skills

Local CRM Skill handlers expose read-only CRM workflows through the shared policy layer.

Current Skills:

- `pipeline-summary`
- `renewal-health`
- `opportunity-view`

Run locally:

```bash
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m company_os_cli crm-skill --name pipeline-summary --user ssabbani --role sales_rep
```
