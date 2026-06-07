# Getting Started

## Purpose

This guide gets opra.ai running locally from a fresh clone.

opra.ai is a free GitHub-native developer preview. It uses local files as the source of truth, local Python commands for validation and workflows, and optional GitHub CLI integration when you want to test live pull requests or issues.

## Prerequisites

Required:

- Git
- Python 3.9 or newer
- A shell such as zsh, bash, or fish

Recommended:

- Python 3.11
- GitHub CLI, `gh`, for live GitHub tests

Optional:

- Node.js 20 or newer for future web UI development

## Clone

```bash
git clone https://github.com/sabbanis/opra.ai.git
cd opra.ai
```

## Configure Python Path

The developer preview can run without packaging or dependency installation:

```bash
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
```

If you use fish:

```fish
set -x PYTHONPATH packages/company_os_core/src:packages/company_os_cli/src
```

## Run The Sanity Checks

```bash
python3 -m company_os_cli doctor
python3 -m unittest discover -s tests
```

Expected:

- `doctor` reports that the repository check passed.
- The test suite passes.

## Validate The Seed CRM Records

```bash
python3 -m company_os_cli validate --file modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli validate --file modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml
```

## Run The CRM Demo Path

```bash
python3 -m company_os_cli index-crm
python3 -m company_os_cli crm-skill --name pipeline-summary --user ssabbani --role sales_rep
```

## Open The Local Dashboard

```bash
python3 apps/api/server.py --repo-root . --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

Stop the API server with `Ctrl+C`.

## Next Steps

- [First CRM Demo](first-crm-demo.md)
- [Governed Proposal Workflow](governed-proposal-workflow.md)
- [GitHub Integration](github-integration.md)
