# Testing Guide

## Full Test Suite

```bash
cd opra.ai
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
python3 -m unittest discover -s tests
```

Expected:

```text
OK
```

## Targeted Tests

Core GitHub integration and CLI behavior:

```bash
python3 -m unittest tests.unit.test_github_proposal_publisher tests.unit.test_cli_commands
```

CRM read model:

```bash
python3 -m unittest tests.unit.test_crm_read_model
```

Governed mutation service:

```bash
python3 -m unittest tests.unit.test_governed_mutation tests.e2e.test_governed_local_write
```

## CLI Smoke Tests

```bash
python3 -m company_os_cli doctor
python3 -m company_os_cli validate --file modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli index-crm
python3 -m company_os_cli crm-skill --name pipeline-summary --user ssabbani --role sales_rep
```

## Browser Dashboard Smoke Test

```bash
python3 apps/api/server.py --repo-root . --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

Expected:

- The dashboard loads.
- CRM summary values appear.
- API server logs requests.

Stop with `Ctrl+C`.

## GitHub Workflow Smoke Test

Use [Governed Proposal Workflow](governed-proposal-workflow.md) to create a proposal and matching source-object change, then open a pull request.

Watch checks:

```bash
gh pr checks --watch
```

Expected:

- `run-tests/python-tests` passes.
- `proposal-check/proposal-check` passes if the proposal and target file match.
- The proposal-check report appears in the Actions summary.
