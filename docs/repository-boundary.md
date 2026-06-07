# Repository Boundary

## Role

`opra.ai` is an external-safe OPRA repository. It may be public or shared
privately with users, evaluators, customers, contributors, or partners.

Treat everything committed here as publishable.

## Allowed

- Product source code intended for the OPRA developer preview.
- Public documentation, onboarding guides, and demo data.
- Public launch copy that can be shown to users.
- Public examples using fictional records and sanitized company names.
- Open-source license and package metadata.

## Not Allowed

- Internal Company OS working notes, planning docs, operating records, or private
  strategy.
- Customer, prospect, partner, employee, investor, or vendor information that was
  not written explicitly for public use.
- Credentials, tokens, API keys, webhook URLs, private keys, or real `.env`
  values.
- Absolute local filesystem paths.
- Links or paths into private sibling repositories.
- Internal go-to-market, roadmap, pricing, fundraising, legal, or procurement
  material.

## Paid Product Boundary

The public project is `opra.ai`.

Future commercial offerings should use separate names, such as `opra Cloud` for
a hosted product and `opra Enterprise` for enterprise security, deployment,
support, and procurement needs.

Commercial naming must not change what this repository is: the open-source
developer artifact.

## Required Check

This repo includes a public hygiene test:

```bash
PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m unittest tests.unit.test_public_repo_hygiene
```

The test scans text files for local paths, private repository references, common
secret formats, and private planning document references. Future external OPRA
repositories should carry the same check or an equivalent one before they are
made public or shared outside the internal team.
