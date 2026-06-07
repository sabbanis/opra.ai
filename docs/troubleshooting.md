# Troubleshooting

## `python3 -m company_os_cli` Cannot Find The Package

Set `PYTHONPATH` from the repository root:

```bash
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
```

Then retry:

```bash
python3 -m company_os_cli doctor
```

## `rg: command not found`

`rg` is ripgrep. It is optional.

Use `grep` instead:

```bash
grep -nE '^(id|version|stage):' modules/crm/objects/accounts/acct_acme.yaml
```

## GitHub CLI Is Not Authenticated

Check:

```bash
gh auth status
```

Authenticate:

```bash
gh auth login -h github.com
```

Mock preview commands do not require `gh` authentication.

## Proposal Validation Fails With Target Hash Mismatch

The proposal `after_hash` must match the target source object in the checkout.

If you created a proposal from a temporary file, copy the proposed after-state into the target path before running PR validation:

```bash
cp /tmp/opra-proposal-demo/acct_acme.yaml modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli validate-proposal-pr --file platform/proposals/mutations/proposal_req_opra_demo.yaml
```

## Proposal Check Comment Is Missing

The GitHub Actions summary is the primary report location.

The PR comment step is best-effort because some GitHub token contexts cannot create issue comments. If comment creation is blocked, check validation still appears in the Actions summary.

## Local Dashboard Does Not Load

Start the API server:

```bash
python3 apps/api/server.py --repo-root . --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

If port `8080` is already in use, choose another port:

```bash
python3 apps/api/server.py --repo-root . --port 8081
```

## Generated Preview Files Show Up In Git Status

Mock GitHub issue previews are local artifacts:

```text
platform/integrations/github/issue_previews/issue_*.yaml
```

Remove generated previews when you are done testing:

```bash
rm platform/integrations/github/issue_previews/issue_*.yaml
```
