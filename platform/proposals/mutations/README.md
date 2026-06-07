# Mutation Proposals

Generated mutation proposal YAML files live here during local development.

These artifacts capture:

- The requested source-object change
- The before and after snapshots
- Schema, domain, and policy results
- Required approvers when policy returns `requires_approval`
- Approval or rejection records
- Apply status and linked audit event ID

The current local flow writes proposal artifacts here instead of mutating source records directly.
Approved proposals can be applied to source objects only if the current source hash still matches
the proposal's `before_hash`.
Future GitHub-native flows will turn these proposals into pull requests.
