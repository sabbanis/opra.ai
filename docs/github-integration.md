# GitHub Integration

## Purpose

opra.ai can use GitHub as a review and evidence surface. Live GitHub operations use the local `git` and `gh` CLIs.

Mock preview commands are available when you want to test without network calls.

## Authenticate GitHub CLI

```bash
gh auth login -h github.com
gh auth status
gh auth setup-git -h github.com
```

## Proposal Pull Requests

Create a proposal artifact first. See [Governed Proposal Workflow](governed-proposal-workflow.md).

Build a mock pull-request preview:

```bash
python3 -m company_os_cli publish-proposal-pr \
  --file platform/proposals/mutations/proposal_req_opra_demo.yaml \
  --repo-url https://github.com/your-org/opra.ai
```

Publish a real pull request:

```bash
python3 -m company_os_cli publish-proposal-pr \
  --file platform/proposals/mutations/proposal_req_opra_demo.yaml \
  --real
```

## Proposal Check Reports

Validate a proposal checkout locally:

```bash
python3 -m company_os_cli validate-proposal-pr \
  --file platform/proposals/mutations/proposal_req_opra_demo.yaml \
  --report-file /tmp/opra-proposal-check.md
```

When running inside GitHub Actions, the proposal-check workflow writes this report to the Actions summary. It also tries to upsert a sticky PR comment. If GitHub token permissions block comment creation, the comment step is best-effort and validation still reports through the Actions summary.

## GitHub Review Evidence

GitHub review evidence is read from:

```bash
gh pr view 1 --json number,url,reviews > /tmp/opra-pr-reviews.json
```

Validate with review evidence:

```bash
python3 -m company_os_cli validate-proposal-pr \
  --file platform/proposals/mutations/proposal_req_opra_demo.yaml \
  --github-review-file /tmp/opra-pr-reviews.json \
  --report-file /tmp/opra-proposal-check.md
```

Approval owner mappings live at:

```text
platform/integrations/github/approval_owners.yaml
```

## GitHub Issue Previews

Create a mock issue preview:

```bash
python3 -m company_os_cli create-github-issue \
  --title "Customer-impacting defect" \
  --body "Acme renewal blocker." \
  --label defect
```

Update a mock issue preview:

```bash
python3 -m company_os_cli update-github-issue \
  --number 1 \
  --state closed \
  --label triaged
```

Preview files are written under:

```text
platform/integrations/github/issue_previews/
```

## Live GitHub Issues

Create a real GitHub issue:

```bash
python3 -m company_os_cli create-github-issue \
  --real \
  --title "opra.ai live issue adapter test" \
  --body "Testing create-github-issue --real." \
  --label test
```

Close it:

```bash
python3 -m company_os_cli update-github-issue \
  --real \
  --number <ISSUE_NUMBER> \
  --state closed
```

## Pull Request Messaging Previews

The local Messages tab models a top-level message as a GitHub pull request and replies as pull-request comments.

Local preview files are written under:

```text
platform/integrations/github/message_threads/
```

The core adapter boundary includes live GitHub operations for requesting PR reviewers, posting PR comments, and listing PR comments. The localhost UI currently uses mock previews so message flows can be tested without network access.
