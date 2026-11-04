---
doc_id: hop-dev-index
title: HOP Design maintainer map
intent: Route maintainers to product contracts, capabilities, verification, and releases.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-10-23
doc_type: index
journey:
  - maintain
---

# HOP Design maintainer map

- [Construction module map](construction-map.md) locates request compilation,
  search, comparison, verification and presentation, with focused test seams.
- [Measure performance](performance.md) separates search, verification and display
  costs, with disposable benchmark outputs and bounded proof reuse.
- [Reduce duplicate verification](plans/verification-cost.md) plans a small
  clean-install gate and shared fidelity checks; runner changes remain proposed.
- [GitHub governance](github-governance.md) defines repository settings,
  required checks, and the evidence unavailable when hosted CI cannot run.
- [Release process](releasing.md) separates GitHub artifacts from PyPI
  publication.
- [Product roadmap](plans/roadmap.md) separates released capabilities, source
  capabilities, and remaining work.
- [Construction usability principles](plans/construction-user-journey.md) define
  intent preservation, progressive detail and molecular handoff expectations.
- [Construction implementation inventory](plans/retained-overhead-construction-inventory.md)
  locates molecular responsibilities and reproducible allocation measurements.
- [Public concept documentation contract](documentation-contract.md) defines
  the claim and non-claim template for new product surfaces.
- [Architecture decisions](../architecture/decisions/) record public contract
  and ownership changes.

Run `bash ./scripts/agent-preflight --strict` before editing. For review, choose
the [verification boundary](performance.md#choose-the-verification-boundary):
`scripts/agent-verify --scope presentation` for molecular views, `--scope source`
for molecular/API behavior, and the default full gate for merge, release,
packaging or uncertain scope. Each scope includes strict preflight and browser
checks. Strict preflight runs the existing
source-layout limit test before the expensive molecular replay suite, so package
sprawl fails early. A local pass does not substitute
for the Linux, permission, integration, and branch-protection evidence produced
by GitHub. Node.js 22 or newer is required for development.

## Delivery decisions and acceptance records

Use the roadmap above for current scope. These records preserve the rationale
and acceptance checks for individual increments.

- [Complete scaffold options](plans/scaffold-options.md) records bounded exploration
  before local selection, explicit retrieval and controlled-set discovery.
- [Product-first discovery](plans/product-first-discovery.md) records desired
  scaffold authoring, permitted preparations and stage-aware comparison.
- [Comparison specifications](plans/comparison-specification.md) records required
  molecular sets, alternative preparations and explicit hairpin handoff.
- [Terminal scaffold comparisons](plans/terminal-scaffold-comparisons.md) records
  terminal intent, stage-qualified controls, required-member search and prior-material reuse.
