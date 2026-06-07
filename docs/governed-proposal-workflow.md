# Governed Proposal Workflow

## Purpose

This workflow shows how opra.ai handles a governed source-object update without bypassing validation, policy, and audit.

The example updates the seed CRM account from `active_customer` to `renewal_due`.

## Setup

```bash
cd opra.ai
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
mkdir -p /tmp/opra-proposal-demo
cp modules/crm/objects/accounts/acct_acme.yaml /tmp/opra-proposal-demo/acct_acme.yaml
```

Update the temporary object:

```bash
perl -0pi -e 's/version: 1/version: 2/' /tmp/opra-proposal-demo/acct_acme.yaml
perl -0pi -e 's/stage: active_customer/stage: renewal_due/' /tmp/opra-proposal-demo/acct_acme.yaml
```

If `perl` is not available, edit the file manually.

Check the changed fields:

```bash
grep -nE '^(id|version|stage):' /tmp/opra-proposal-demo/acct_acme.yaml
```

## Create A Proposal Artifact

```bash
python3 -m company_os_cli propose-mutation \
  --file /tmp/opra-proposal-demo/acct_acme.yaml \
  --repo-root . \
  --user ssabbani \
  --role founder \
  --action update \
  --field stage \
  --request-id req_opra_demo
```

Expected:

```text
platform/proposals/mutations/proposal_req_opra_demo.yaml
```

The source object is not changed by proposal creation.

## Validate The Proposal As A PR Checkout

For local validation, copy the proposed object state into the target path:

```bash
cp /tmp/opra-proposal-demo/acct_acme.yaml modules/crm/objects/accounts/acct_acme.yaml
```

Validate:

```bash
python3 -m company_os_cli validate-proposal-pr \
  --file platform/proposals/mutations/proposal_req_opra_demo.yaml \
  --report-file /tmp/opra-proposal-report.md
```

View the report:

```bash
sed -n '1,140p' /tmp/opra-proposal-report.md
```

Expected:

- Status is `passed`.
- Missing approvers are `none`.
- Before and after hashes are present.

## Cleanup Local Demo Edits

If you are not opening a PR, restore the source object and remove the demo proposal:

```bash
git checkout -- modules/crm/objects/accounts/acct_acme.yaml
rm platform/proposals/mutations/proposal_req_opra_demo.yaml
```

Use `git status --short` to confirm your local tree.
