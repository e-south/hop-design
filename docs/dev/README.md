---
doc_id: hop-dev-index
title: HOP Design maintainer map
intent: Route maintainers to governance, release, and migration work.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# HOP Design maintainer map

- [GitHub governance](github-governance.md) defines repository settings,
  required checks, and the evidence unavailable when hosted CI cannot run.
- [Release process](releasing.md) separates GitHub artifacts from PyPI
  publication.
- [Implementation and migration roadmap](plans/roadmap.md) orders package
  readiness, downstream adoption, and predecessor removal.
- [Architecture decisions](../architecture/decisions/) record public contract
  and ownership changes.

Run `bash ./scripts/agent-preflight --strict` before editing and
`bash ./scripts/agent-verify` before review. A local pass does not substitute
for the Linux, permission, integration, and branch-protection evidence produced
by GitHub.
