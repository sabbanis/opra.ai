# Product Test Plan

## Purpose

This plan tests opra.ai as a GitHub-native governed workflow layer for business operations.

Do not test it only as a CRM. CRM is one demo module. The product claim to test is:

> A user can make governed business changes through persona-scoped modules, validation, policy checks, approvals, proposals, publishing, and audit evidence.

## Test Rules

- Test from a clean working tree unless the test explicitly creates files.
- Use seeded demo users only.
- Use passcode `demo` for seeded users.
- Do not use real customer, employee, candidate, or production data.
- Record every failure with the exact user, screen, action, expected result, and actual result.
- A workflow is not complete until you can find the related Activity or proposal evidence.

## Environment

From the repository root:

```bash
git status --short
export PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src
python3 -m unittest discover -s tests
python3 -m company_os_cli doctor
```

Expected:

- `git status --short` is empty before testing.
- Unit tests pass.
- `doctor` reports the repository check passed.

## Seed Record Validation

Run:

```bash
python3 -m company_os_cli validate --file modules/crm/objects/accounts/acct_acme.yaml
python3 -m company_os_cli validate --file modules/crm/objects/opportunities/opp_acme_renewal_2026.yaml
```

Expected:

- Both records validate.
- No schema errors appear.

## CRM Read Model And Skill

Run:

```bash
python3 -m company_os_cli index-crm
python3 -m company_os_cli crm-skill --name pipeline-summary --user ssabbani --role sales_rep
```

Expected:

- CRM read model builds.
- Pipeline summary returns readable account or opportunity information.
- No traceback appears.

## Dashboard Startup

Run:

```bash
python3 apps/api/server.py --repo-root . --port 8080
```

Open:

```text
http://127.0.0.1:8080/
```

Expected:

- Dashboard loads.
- Sign-in screen appears.
- No browser console errors block usage.

## Persona Access Matrix

For each persona, sign out before testing the next one.

| UID | Expected Access | Expected Blocks |
| --- | --- | --- |
| `owner` | Users, Customers, Delivery, People, records, proposals, publishing, activity | None in normal demo flow |
| `admin` | Users, Customers, Delivery, People, records, proposals, publishing, activity | None in normal operations flow |
| `customer_lead` | Customers, customer records, proposals, activity | Users, Delivery, People |
| `customer_operator` | Customers, customer records, proposals, activity | Users, Delivery, People, Publishing |
| `engineering_lead` | Delivery, delivery records, proposals, activity | Users, Customers, People |
| `support_engineer` | Delivery, delivery records, proposals, activity | Users, Customers, People, release creation |
| `people_ops` | People, people records, proposals, activity | Users, Customers, Delivery |
| `hiring_manager` | People, hiring records, proposals, activity | Users, Customers, Delivery, employee/time-off changes |

Pass criteria:

- A persona only sees intended navigation items.
- A persona cannot use hidden or forbidden modules through the UI.
- Forbidden API calls return access denied if tested directly.

## Manual Workflow Tests

### Owner

Sign in:

- UID: `owner`
- Passcode: `demo`

Steps:

1. Open Users.
2. Confirm seeded users exist.
3. Open Customers.
4. Open Delivery.
5. Open People.
6. Open Workbench.
7. Create one safe test item in any module.
8. Run Validate.
9. Run Policy Check.
10. Save or propose the change.
11. Open Activity.

Expected:

- Owner can reach all modules.
- Owner can manage users.
- Created or proposed work leaves Activity evidence.

### Company OS Admin

Sign in:

- UID: `admin`
- Passcode: `demo`

Steps:

1. Open Users.
2. Confirm every user has exactly one persona.
3. Open each module once.
4. Open Workbench.
5. Load an existing item without changing it.
6. Run Validate.
7. Open Activity.

Expected:

- Admin can operate all modules.
- Admin can inspect users.
- Validation works on existing records.
- Activity is readable.

### Customer Operator

Sign in:

- UID: `customer_operator`
- Passcode: `demo`

Steps:

1. Open Customers.
2. Find Acme.
3. Open Workbench.
4. Choose Opportunity.
5. Fill every generated field.
6. Run Validate.
7. Run Policy Check.
8. Save or create a proposal.
9. Open Activity.

Expected:

- Customer Operator can work only in Customers.
- Opportunity validates.
- Policy result is understandable.
- Activity shows the customer work.
- Users, Delivery, People, and Publishing are unavailable.

### Customer Lead

Sign in:

- UID: `customer_lead`
- Passcode: `demo`

Steps:

1. Open Customers.
2. Review customer health, ARR, renewal, and pipeline.
3. Open Proposals or Approvals if available.
4. Review a customer-related proposal.
5. Approve or reject with a reason.
6. Open Activity.

Expected:

- Customer Lead can review customer work.
- Decision requires or records a reason.
- Activity shows approval evidence.

### Support Engineer

Sign in:

- UID: `support_engineer`
- Passcode: `demo`

Steps:

1. Open Delivery.
2. Open Workbench.
3. Choose Defect or Incident.
4. Fill severity, state, owner team, and next step.
5. Run Validate.
6. Run Policy Check.
7. Save or create a proposal.
8. Open Activity.

Expected:

- Support Engineer can create defects and incidents.
- Support Engineer cannot create releases.
- Delivery work has severity, state, owner team, and next step.
- Activity shows support evidence.

### Engineering Lead

Sign in:

- UID: `engineering_lead`
- Passcode: `demo`

Steps:

1. Open Delivery.
2. Review defects, incidents, releases, and RCAs.
3. Open Workbench.
4. Choose Defect, Incident, or Release.
5. Run Validate.
6. Run Policy Check.
7. Save or propose the work.
8. Open Activity.

Expected:

- Engineering Lead can use delivery object types.
- Release readiness can be captured.
- Delivery changes leave evidence.

### Hiring Manager

Sign in:

- UID: `hiring_manager`
- Passcode: `demo`

Steps:

1. Open People.
2. Focus on jobs, candidates, interviews, offers, and onboarding.
3. Open Workbench.
4. Choose Job or Candidate.
5. Fill stage, source, and next step.
6. Run Validate.
7. Run Policy Check.
8. Save or create a proposal.
9. Open Activity.

Expected:

- Hiring Manager can create hiring-related work.
- Hiring Manager cannot manage users.
- Hiring Manager cannot change Customers or Delivery.
- Activity shows hiring evidence.

### People Ops

Sign in:

- UID: `people_ops`
- Passcode: `demo`

Steps:

1. Open People.
2. Review jobs, candidates, employees, onboarding, and time off.
3. Open Workbench.
4. Choose Job, Candidate, Employee, or Time Off.
5. Run Validate.
6. Run Policy Check.
7. Save or create a proposal.
8. Open Activity.

Expected:

- People Ops can operate People records.
- Sensitive records use appropriate visibility.
- People work leaves Activity evidence.

## Negative Tests

Run these after positive persona tests.

### Bad Sign-In

Steps:

1. Try UID `owner` with passcode `wrong`.
2. Try an unknown UID.

Expected:

- Sign-in fails.
- No session is created.

### Forbidden Module

Steps:

1. Sign in as `customer_operator`.
2. Attempt to access Delivery.
3. Attempt to access People.
4. Attempt to access Users.

Expected:

- UI hides or blocks forbidden areas.
- Any direct API attempt returns access denied.

### Missing Required Field

Steps:

1. Sign in as `customer_operator`.
2. Open Workbench.
3. Choose Opportunity.
4. Leave a required field blank.
5. Run Validate.

Expected:

- Validation fails.
- Error names the missing or invalid field.
- Invalid work is not saved as a valid business record.

### Wrong Persona Object Type

Steps:

1. Sign in as `support_engineer`.
2. Attempt to create a Release.

Expected:

- Release creation is unavailable or denied.
- No release record is created.

### People Data Boundary

Steps:

1. Sign in as `customer_operator`.
2. Attempt to view or create People records.

Expected:

- Access is denied.
- People data is not visible.

## Proposal And Approval Test

Steps:

1. Sign in as a scoped operator.
2. Create a work item that requires approval.
3. Save it as a proposal.
4. Sign out.
5. Sign in as the appropriate lead, admin, or owner.
6. Review the proposal.
7. Reject it with a reason.
8. Confirm status and Activity evidence.
9. Create or update another proposal.
10. Approve it.
11. Confirm status and Activity evidence.

Expected:

- Proposal records show the correct status.
- Approval and rejection require meaningful reasons.
- Activity shows who made the decision.
- Unauthorized personas cannot approve work outside their scope.

## GitHub Integration Smoke Test

Only run this after local tests pass.

Check authentication:

```bash
gh auth status
```

Recommended order:

1. Test mock GitHub Issue previews.
2. Test mock proposal PR previews.
3. Test live GitHub issue creation in a fork or disposable branch.
4. Test live proposal PR creation only when you are comfortable with the output.

Expected:

- Mock preview tests do not require network access.
- Live tests use the configured GitHub account.
- Generated PR or issue content matches the local proposal.

## Adaptability Test

This test proves whether the product is easy to adapt beyond CRM.

Choose one fake module idea:

- Vendors
- Procurement
- Security exceptions
- Contract review
- Customer onboarding

Answer these before writing code:

1. What object types exist?
2. Which fields are required?
3. Which personas can read records?
4. Which personas can create records?
5. Which personas can approve changes?
6. Which changes require approval?
7. What seed data proves the workflow?
8. What dashboard summary proves the data is useful?
9. What validation errors should appear?
10. What audit evidence should exist?

Pass criteria:

- You can describe the module without CRM vocabulary.
- The module has at least one object type, one persona, one policy, one seed record, and one test.
- A new user can run the module's happy path from sign-in to Activity evidence.

## Product Readiness Checklist

The product is demo-ready when:

- Unit tests pass.
- CLI doctor passes.
- Seed records validate.
- Dashboard starts locally.
- Every seeded persona can sign in.
- Persona access matches the matrix.
- Each module supports one complete governed workflow.
- Negative tests block invalid or unauthorized work.
- Proposal approval and rejection are visible in Activity.
- README explains the product without requiring CRM expertise.
- Persona onboarding explains what each persona can do.
- A non-CRM module can be explained using the same module-pack pattern.

## Failure Log Template

Copy this for every issue:

```text
Date:
Tester:
Persona:
Browser:
Command or screen:
Action:
Expected:
Actual:
Evidence path or screenshot:
Severity:
Notes:
```
