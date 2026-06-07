# Hacker News Launch Draft: opra.ai

## Readiness Call

Verdict: ready for Hacker News after the license update is pushed and the public GitHub README matches this repo.

Green:

- `PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m company_os_cli doctor` passes.
- `PYTHONPATH=packages/company_os_core/src:packages/company_os_cli/src python3 -m unittest discover -s tests` passes with 114 tests.
- The README has a copy-pasteable local quickstart.
- The demo path is concrete: CRM records, governed mutations, proposals, GitHub review evidence, audit output, API, browser UI, and Skills.
- The source repository now has an Apache-2.0 license, which is permissive enough for forks and clear enough for HN.

Remaining launch check:

- The public GitHub repository should show the same README and `LICENSE` file before posting.

Positioning rule:

- Do not lead HN with the carousel headline. It is good for LinkedIn/X, but HN should get the technical mechanism first and the provocation second.

## HN Submission

Title:

```text
Show HN: opra.ai - GitHub-native governance for agentic business workflows
```

URL:

```text
https://github.com/sabbanis/opra.ai
```

Post type:

```text
Submit as a URL post, then immediately add the first comment below.
```

Visual:

```text
The GitHub README includes the governed operating loop diagram. Do not upload
carousel images to Hacker News.
```

## First Comment

```text
I built opra.ai as a free developer preview of a GitHub-native operating layer for business workflows.

The bet is that if AI agents are going to operate parts of a company, they should not mutate business systems through hidden write paths. They should go through the same kind of governed path we already expect for production code:

intent -> policy -> proposal -> PR review -> source objects -> audit evidence -> dashboards + Skills

Today the repo includes a local CRM demo path, human-readable source records, schema validation, RBAC and approval policy, governed local writes, proposal artifacts, GitHub PR/review evidence mapping, audit events, a local API, browser workspace, and Skills that read from the same source state.

It is intentionally early. CRM is the strongest path right now; HR and issue management are scaffolds. The CLI package names still say company_os during the preview.

What I am looking for from HN:

Where does this model break?
Would you trust a governed repo-backed write path more or less than normal SaaS automation?
What is missing before this is useful to another developer-led team?

I am not claiming SaaS is dead. The narrower claim is that black-box SaaS as the default system of record becomes negotiable once agents need safe, reviewable ways to act.
```

## Shorter First Comment

Use this if you want less manifesto and more punch:

```text
I built opra.ai because I do not think agentic business workflows should mutate SaaS state through hidden write paths.

The core loop is:

intent -> policy -> proposal -> PR review -> source files -> audit evidence -> dashboards + Skills

The developer preview has a local CRM path, source-controlled records, schema validation, RBAC/approval policy, governed writes, proposal artifacts, GitHub review evidence, audit events, API/UI surfaces, and Skills reading from the same state.

CRM is the real demo path today. HR and issues are scaffolds. I am looking for critique from people who have operated real systems: where does this model break?

Repo: https://github.com/sabbanis/opra.ai
```

## Higher-Risk Titles

```text
Show HN: I made a GitHub-native operating layer for AI-run business workflows
```

```text
Show HN: opra.ai - Governed company state as files, PRs, and audit evidence
```

```text
Show HN: opra.ai - An open developer preview for agent-operable company state
```

## Do Not Use As The HN Title

```text
Who Killed SaaS? Ain't Me.
```

Reason: it is a strong social hook, but HN will likely read it as vague marketing unless the technical artifact earns attention first.

## Social Post With Carousel

Use this copy for social follow-up posts. Keep source paths and private working
repo references out of public launch docs.

Copy:

```text
Who killed SaaS?

Ain't me.

But agentic AI exposes the weak spot in old SaaS:

the app owns the data,
the workflow,
the permissions,
the audit trail,
and then rents your company back through APIs and dashboards.

That worked when humans clicked screens.

It breaks when agents need to act.

Agents need governed company state:

- source-controlled records
- permissions before action
- proposals before mutation
- reviewable approvals
- audit evidence
- dashboards and Skills from the same truth

That is the bet behind opra.ai.

SaaS is not dead.

But black-box SaaS as the default system of record is now negotiable.

Fork the free developer preview:
https://github.com/sabbanis/opra.ai

Tell me where this model breaks.
```

## Preflight Before Posting

- Confirm the `LICENSE` file and README license section are visible on GitHub.
- Confirm the public GitHub README matches the local README.
- Run the exact quickstart from a fresh clone.
- Make sure the first screenshot or GIF in the README shows the browser workspace or proposal flow.
- Submit the GitHub repo URL to HN, not a carousel or landing page.
- Add the first comment within the first minute.
