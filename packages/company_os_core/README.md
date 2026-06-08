# opra Core Package

Core platform package for opra.ai.

This package owns the first platform primitives:

- Core domain models
- Deterministic YAML/JSON serialization
- Stable object hashing
- Dependency-free base schema validation
- Local filesystem object storage
- RBAC evaluation
- Policy and approval requirement evaluation
- Append-only audit event writing
- Governed mutation service that composes schema, policy, storage, and audit
- CRM account and opportunity models with schema helpers
- CRM lifecycle validation for governed stage updates
- CRM dashboard read-model builder
- Skill contract primitives and local CRM Skill handlers
- Workspace CRUD Skill descriptors
- Dependency-free local read API router
- Mutation proposal service for reviewable local change proposals
- Proposal approval, rejection, apply, and audit evidence flow
- GitHub adapter boundary, mock publisher, and GitHub CLI-backed publisher
- GitHub Issue create/update adapter with mock and GitHub CLI implementations
- Proposal PR validation for GitHub Actions checks
- GitHub approval owner mapping and PR review evidence parsing
- Markdown proposal validation reports for check summaries and PR comments
- Proposal merge recorder for post-merge audit evidence

Future slices will add indexing primitives, adapters, and shared utilities.
