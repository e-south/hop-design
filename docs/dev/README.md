---
doc_id: hop-dev-index
title: HOP Design maintainer map
intent: Route maintainers to product contracts, capabilities, verification, and releases.
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
- [Product roadmap](plans/roadmap.md) separates released capabilities, source
  capabilities, and remaining work.
- [Construction implementation inventory](plans/retained-overhead-construction-inventory.md)
  locates molecular responsibilities and reproducible allocation measurements.
- [Public concept documentation contract](documentation-contract.md) defines
  the claim and non-claim template for new product surfaces.
- [Architecture decisions](../architecture/decisions/) record public contract
  and ownership changes.

Run `bash ./scripts/agent-preflight --strict` before editing and
`bash ./scripts/agent-verify` before review. A local pass does not substitute
for the Linux, permission, integration, and branch-protection evidence produced
by GitHub.
