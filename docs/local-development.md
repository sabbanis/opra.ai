# Local Development Setup

## Purpose

This document describes the local setup for developing and testing opra.ai.

## Repository

```bash
git clone https://github.com/sabbanis/opra.ai.git
cd opra.ai
```

## Python Environment

The current developer preview has no required third-party Python dependencies for the main test suite.

Use the source paths directly:

```bash
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
python3 -m unittest discover -s tests
```

Optional virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

## GitHub CLI

Install and authenticate `gh` only if you want to test live GitHub pull requests or issues:

```bash
gh auth login -h github.com
gh auth status
gh auth setup-git -h github.com
```

Mock preview commands do not require GitHub authentication.

## Local Configuration

Do not commit secrets.

Ignored local env files:

```text
.env
.env.local
```

Template:

```text
.env.example
```

## Common Commands

```bash
python3 -m company_os_cli doctor
python3 -m company_os_cli validate --file modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli inspect --file modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli index-crm
python3 -m company_os_cli crm-skill --name pipeline-summary --user ssabbani --role sales_rep
python3 apps/api/server.py --repo-root . --port 8080
```

## GitHub Preview Commands

Create a mock GitHub issue preview:

```bash
python3 -m company_os_cli create-github-issue \
  --title "Customer-impacting defect" \
  --body "Acme renewal blocker." \
  --label defect
```

Update a mock GitHub issue preview:

```bash
python3 -m company_os_cli update-github-issue \
  --number 1 \
  --state closed \
  --label triaged
```

Generated previews live under:

```text
platform/integrations/github/issue_previews/
```

Remove generated preview files when you no longer need them.
