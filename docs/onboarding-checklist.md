# Onboarding Checklist

Use this checklist when evaluating opra.ai locally or preparing a fork.

## Local Environment

- [ ] Git is installed.
- [ ] Python 3.9 or newer is installed.
- [ ] Repository is cloned.
- [ ] `PYTHONPATH` is set to `packages/company_os_core/src:packages/company_os_cli/src`.
- [ ] `python3 -m company_os_cli doctor` passes.
- [ ] `python3 -m unittest discover -s tests` passes.

## CRM Demo

- [ ] Account seed record validates.
- [ ] Opportunity seed record validates.
- [ ] CRM read model builds with `index-crm`.
- [ ] Pipeline Skill runs with `crm-skill --name pipeline-summary`.
- [ ] Local API starts with `python3 apps/api/server.py --repo-root . --port 8080`.
- [ ] Browser dashboard loads at `http://127.0.0.1:8080/`.

## Governed Workflow

- [ ] A proposal artifact can be created with `propose-mutation`.
- [ ] The target object can be updated to match the proposal after-state.
- [ ] `validate-proposal-pr` passes for the matching proposal checkout.
- [ ] A Markdown proposal report can be generated with `--report-file`.

## Optional GitHub Integration

- [ ] `gh auth status` passes.
- [ ] Mock GitHub issue preview can be created.
- [ ] Mock GitHub issue preview can be updated.
- [ ] Optional live GitHub issue test is created and closed.
- [ ] Optional proposal PR workflow test passes.

## Cleanup

- [ ] Temporary proposal artifacts are removed or committed intentionally.
- [ ] Temporary source-object edits are reverted or committed intentionally.
- [ ] Generated issue previews are removed when no longer needed.
- [ ] `git status --short` shows only expected changes.
