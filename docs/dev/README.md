# HOP Design maintainer map

- [Construction module map](construction-map.md) locates request compilation,
  search, comparison, verification and presentation, with focused test seams.
- [Measure performance](performance.md) separates search, verification and display
  costs, with disposable benchmark outputs and verification results reused only
  within their declared scope.
- [Verification design](plans/verification-cost.md) records the separation of
  source tests, routine installation checks and release qualification. The
  performance guide above defines the current gate selection.
- [Compact checkpoints](plans/checkpoint-storage.md) plans bounded storage,
  cross-version continuation and content-verified migration.
- [GitHub governance](github-governance.md) defines repository settings,
  required checks, and the evidence unavailable when hosted CI cannot run.
- [Release HOP](releasing.md) publishes verified files to GitHub and PyPI.
- [Product roadmap](plans/roadmap.md) separates released capabilities, source
  capabilities, and remaining work.
- [Construction usability principles](plans/construction-user-journey.md) define
  intent preservation, progressive detail and molecular handoff expectations.
- [Construction implementation inventory](plans/retained-overhead-construction-inventory.md)
  locates molecular responsibilities and reproducible allocation measurements.
- [Write useful documentation](documentation-contract.md) covers task flow,
  examples, references and readable navigation.
- [Architecture decisions](../architecture/decisions/) record public contract
  and ownership changes.

Run `bash ./scripts/agent-preflight --strict` before editing. For review,
choose the [verification
boundary](performance/verification.md#choose-the-verification-boundary):
`scripts/agent-verify --scope presentation` for molecular views,
`--scope source` for molecular/API behavior, and the default full gate for
merge, release, packaging or uncertain scope. Full defaults to extended
installation; CI may select `--distribution routine` for documented
non-packaging changes. Each scope includes strict preflight and browser
checks. Strict preflight checks source-layout limits before the expensive
molecular replay suite. GitHub additionally verifies Linux behavior,
permissions, integration, and branch protection. Node.js 22 or newer is
required for development.

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
