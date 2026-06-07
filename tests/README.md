# Tests

Cross-package tests live here.

- `unit`: pure logic and package-level tests
- `integration`: adapter and service boundary tests
- `e2e`: end-to-end user journey tests

Public repository hygiene is enforced by
`tests/unit/test_public_repo_hygiene.py`. It scans external-safe OPRA repos for
local paths, private repository references, common secret formats, and private
planning document references.
