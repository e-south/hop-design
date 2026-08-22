---
doc_id: hop-architecture
title: HOP Design architecture
intent: Define ownership, dependency direction, and module boundaries.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-21
---

# HOP Design architecture

HOP Design is a standalone modular monolith: one repository, one Python
distribution, one public API, and no dependency on caller repositories.

## Product boundary

The deterministic core has two related compilation spines:

```text
HopSpec -> check/resolve -> HopPlan -> HopBundle
MethodRequest -> resolve states -> MethodPlan -> MethodBundle
```

HOP owns its ontology, minimal DNA/IUPAC kernel, junction contracts, route
resolution, bounded processing-geometry discovery, explicit molecular-event
evaluation, paired non-payload stem context, route-material binding,
deterministic artifacts, typed workflow views, and integrity
verification. It does not own workspaces, runs, samples, observations,
evidence, assay semantics, larger construct placement, private processing
catalogs, or private application profiles. Callers link their own records
through neutral external references.

## Layer direction

```text
models
  <- kernel and catalogs and deterministic encoders
  <- design use cases
  <- public API
  <- CLI and future agent adapters
```

- `models` contains strict data contracts and imports no higher HOP layer.
- `kernel` owns pure derivations and content identity.
- `catalog` contains only generic, versioned public demonstration data.
- `export` encodes and verifies artifacts without owning scientific policy;
  renderers consume typed view state and do not recompute molecular state.
- `design` checks, resolves, and compiles through the lower layers.
  `compile.py` orchestrates use cases; `assembly.py` owns final plan and bundle
  construction; `bundle.py` replays spec-to-bundle semantics over the
  lower-level integrity reader; `result.py` owns the write-capable compilation
  result.
- A method bundle is separate from a design bundle. It proves how one named
  method request resolves into molecular states and exported physical products;
  it does not redefine design identity or claim destination readiness.
- `api` is the small stable Python facade.
- `cli` adapts user input to the public API and contains no derivations.

`scripts/check_architecture.py` enforces absolute and relative imports, maps the
root `api.py` and `cli.py` modules explicitly, and fails on unknown first-party
layers. The root facade and serialization module are narrow documented
exceptions. Add an abstraction only when a second real implementation or
consumer makes the seam necessary.

## Current product slices

The built-in `generic-direct-synthesis@1` route remains intentionally small. It
exercises exact and symbolic payload handling, both canonical junction nouns,
typed spans, plan locking, JSON/FASTA export, and bundle verification. It makes
no claim of representing a lab processing protocol.

The explicit-mechanics path accepts foldback and basal inputs plus an optional
terminal nick and duplex release. Without a terminal nick it emits a
`component_assembly`: validated components, a derived paired payload, a
five-part insert, and route-neutral QA views without a discovery or processing
claim. With a terminal nick it emits `resolved_events` and the corresponding
state transitions. A release event requires that resolved route. Pure kernels
derive pairing and strand state; the design layer applies caller-supplied
feasibility policy. See
[ADR 0008](docs/architecture/decisions/0008-inherited-component-assembly.md).

HOP does not resolve private agent identity, historical lineage, or eligibility
from neighboring repositories. Sanitized contract fixtures cover the public
mechanics, but predecessor differential equality and downstream cutover remain
separate migration gates in [the roadmap](docs/dev/plans/roadmap.md).

Explicit foldback evaluation also represents a cap-only junction with zero
retained and returning paired bases. It emits no synthetic pair observations;
bounded arm search remains limited to nonempty retained tracts. See
[ADR 0007](docs/architecture/decisions/0007-cap-only-foldback-junctions.md).

Discovery is distinct from compilation. `search_nicking_placements` evaluates
one strand-compatible orientation per caller-supplied nicking agent and returns
exact or nearest geometry under node and result budgets. It neither constructs
filler sequence nor applies commercial or application rank. Selected explicit
events enter the existing compiler boundary. `search_basal_candidates`
enumerates exact four-position arm pairs only inside caller-authored IUPAC
domains, applies an explicit constraint profile, and orders returned candidates
canonically by physical profile and sequence rather than desirability. It does
not discover an enzyme route or copy application profile buckets. Optional structure predictors and
additional renderers consume plan-owned artifacts without changing molecular
validity; see [ADR 0006](docs/architecture/decisions/0006-discovery-compilation-and-assessment.md).

Resolved routes use an explicit molecular-state graph. A released active
product must equal the next foldback input. Foldback and basal junctions are
evaluated independently. A terminal-nick transition consumes the basal
junction, and insert assembly consumes the terminal-nicked basal state, the
foldback junction, and the authored payload. Every sequence is stored 5′→3′.
Junction evaluations and catalog defaults use the same physical
pair-observation types.
