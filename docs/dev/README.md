---
doc_id: hop-dev-index
title: HOP Design maintainer map
intent: Route maintainers to governance, release, and migration work.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-31
doc_type: index
journey:
  - maintain
---

# HOP Design maintainer map

- [GitHub governance](github-governance.md) defines repository settings,
  required checks, and the evidence unavailable when hosted CI cannot run.
- [Release process](releasing.md) separates GitHub artifacts from PyPI
  publication.
- [Implementation and migration roadmap](plans/roadmap.md) orders package
  readiness, downstream adoption, and predecessor removal.
- [Historical construction realignment audit](HOP-construction-realignment-gap-audit.md)
  records the completed pre-v0.1.0a8 gap analysis and routes current status to
  the roadmap and accepted architecture decisions.
- [Linear-source product closure audit](HOP-linear-source-product-closure-audit.md)
  maps source preparation, source partition, auxiliary materials, and endpoint
  navigation to one portable HOP result.
- [Public concept documentation contract](documentation-contract.md) defines
  the claim and non-claim template for new product surfaces.
- [Architecture decisions](../architecture/decisions/) record public contract
  and ownership changes.

Run `bash ./scripts/agent-preflight --strict` before editing and
`bash ./scripts/agent-verify` before review. A local pass does not substitute
for the Linux, permission, integration, and branch-protection evidence produced
by GitHub.
