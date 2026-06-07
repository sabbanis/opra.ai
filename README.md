# opra.ai

Free, GitHub-native operating layer for governed business workflows.

opra.ai stores business records as human-readable files, validates them locally, runs governed mutations through RBAC and approval policy, emits audit evidence, and exposes demo workflows through CLI, API, browser UI, GitHub pull requests, and Skills.

This repository is the free developer-preview edition. It is meant for local evaluation, forks, demos, and self-directed experimentation.

## What You Can Do Today

- Validate CRM source records.
- Inspect source records as JSON.
- Run governed local writes with audit events.
- Create mutation proposal artifacts.
- Validate proposal pull requests with GitHub Actions.
- Map GitHub reviews into approval evidence.
- Generate proposal check reports for Actions summaries.
- Build local CRM dashboard read models.
- Run local CRM Skills.
- Use a browser CRM dashboard from a local API server.
- Create and update mock GitHub Issue previews.
- Publish real proposal PRs and GitHub Issues with `gh` when you choose to use live GitHub integration.

## Current Limits

- The CLI module names are still `company_os_cli` and `company_os_core` during this developer preview.
- CRM is the primary complete demo path.
- Issue Management and HR scaffolds exist, but CRM has the strongest local workflow coverage.
- The browser UI is a local demo UI, not a polished local application.
- GitHub integration uses the local `git` and `gh` CLIs for live operations.

## Quickstart

```bash
git clone https://github.com/sabbanis/opra.ai.git
cd opra.ai
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
python3 -m unittest discover -s tests
python3 -m company_os_cli doctor
```

Validate the CRM seed records:

```bash
python3 -m company_os_cli validate --file modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli validate --file modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml
```

Build the CRM read model and run a Skill:

```bash
python3 -m company_os_cli index-crm
python3 -m company_os_cli crm-skill --name pipeline-summary --user ssabbani --role sales_rep
```

Run the local browser dashboard:

```bash
python3 apps/api/server.py --repo-root . --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

## Onboarding Docs

Start here:

- [Getting Started](docs/getting-started.md)
- [Onboarding Checklist](docs/onboarding-checklist.md)
- [Local Development Setup](docs/local-development.md)
- [First CRM Demo](docs/first-crm-demo.md)
- [Governed Proposal Workflow](docs/governed-proposal-workflow.md)
- [GitHub Integration](docs/github-integration.md)
- [Testing Guide](docs/testing-guide.md)
- [Troubleshooting](docs/troubleshooting.md)

## Repository Layout

```text
modules/       Product modules: CRM, Issues, HR
platform/      RBAC, audit, dashboards, GitHub integration, proposals
apps/          Local API, browser UI, workers scaffold
packages/      Shared Python packages
demos/         Seed data, scripts, narratives
docs/          Free onboarding docs
tests/         Unit, integration, and e2e tests
```

## Local Check

Run the current no-dependency test suite:

```bash
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m unittest discover -s tests
```

Run the CLI doctor command:

```bash
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m company_os_cli doctor
```

## License

License information has not been finalized in this split. Do not assume redistribution terms beyond normal GitHub access until a license file is added.
