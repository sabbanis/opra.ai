# opra CLI Package

Command-line interface for opra.ai.

The initial CLI exposes:

- `doctor`: validate the repository foundation
- `validate --file`: validate a YAML source object against the base, account, or opportunity schema
- `inspect --file`: print a YAML source object as JSON
- `policy-check --file`: run a local demo RBAC and approval check
- `audit-record`: write an append-only audit event
- `governed-write`: validate, authorize, store, and audit an object file
- `propose-mutation`: validate, authorize, and write a reviewable proposal artifact
- `approve-proposal`: record approval against a proposal artifact
- `reject-proposal`: reject a proposal artifact before execution
- `apply-proposal`: apply an approved proposal and write audit evidence
- `publish-proposal-pr`: build a mock GitHub PR preview or publish a real PR with `--real`
- `create-github-issue`: create a mock GitHub Issue preview or create a real issue with `--real`
- `update-github-issue`: update a mock GitHub Issue preview or update a real issue with `--real`
- `validate-proposal-pr`: validate proposal, target files, and optional GitHub review evidence in a PR checkout; can write a Markdown report with `--report-file`
- `record-proposal-merge`: mark a merged proposal applied and write audit evidence, including optional GitHub review approvals
- `index-crm`: build the local CRM dashboard read model
- `crm-skill`: run a local CRM Skill handler through the demo policy layer

Future commands will cover imports, indexing, demos, backups, and restore.
