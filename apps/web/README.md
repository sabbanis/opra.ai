# Web App

Localhost Company OS dashboard. The UI uses the same governance services as CLI, Skills, API, and publishing workflows.

The browser workspace is served by the local API server at `http://127.0.0.1:8080/`.

Current surface:

- Local Company OS sign-in, self-registration for operator personas, and owner/admin user management
- Company OS home dashboard with KPIs, attention signals, approval queue, recent activity, and quick actions
- Customers dashboard with accounts, opportunities, renewal health, and local Skill results
- Delivery workspace for defects, incidents, feature requests, components, releases, and RCAs
- People workspace for jobs, candidates, employees, onboarding, policy acknowledgments, and time off
- Governed Workbench for create, read, update, delete, validation, policy checks, and approval requests
- Approval review and commit workflow, publishing drafts, and activity evidence

Personas:

- Owner: full operating dashboard, all modules, approvals, publishing, activity, and user administration
- Company OS Admin: system operations, all modules, approvals, publishing, activity, and user administration
- Customer Lead: customer pipeline, renewals, customer approvals, and CRM work items
- Customer Operator: customer account and opportunity work items
- Engineering Lead: delivery work, defects, incidents, releases, and engineering evidence
- Support Engineer: support defects, incidents, RCAs, and support evidence
- People Ops: hiring, employee, onboarding, policy, and time-off work items
- Hiring Manager: open roles, candidates, interviews, offers, and onboarding requests

Seeded local users live in `platform/identity/users.json`. Every seeded user can sign in with passcode `demo`.
