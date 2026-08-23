---
doc_id: hop-architecture
title: HOP Design architecture
intent: Define ownership, dependency direction, and module boundaries.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
doc_type: explanation
---

# HOP Design architecture

HOP Design is a standalone modular monolith: one repository, one Python
distribution, one public API, and no dependency on caller repositories.

## Product boundary

The deterministic core has two sibling compilation spines:

```text
HopSpec -> design derivation -> HopPlan -> HopBundle
MethodRequest -> resolve states -> MethodPlan -> MethodBundle
```

HOP owns its ontology, minimal DNA/IUPAC kernel, junction contracts, design
resolution, bounded processing-geometry discovery, explicit molecular-event
evaluation, paired non-payload stem context, route-material binding,
deterministic artifacts, typed workflow views, and integrity
verification. It does not own workspaces, runs, samples, observations,
experimental evidence, assay semantics, larger construct placement, private processing
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
  Model-adjacent semantic replay modules may contain pure, deterministic
  construction validation when a serialized contract must reject molecular
  drift without importing a higher layer. They are internal authorities, not
  public use cases, and both producers and model validators call the same
  replay function where construction and validation share a derivation.
- `models/physical.py` is the model-safe authority for literal pair kinds,
  opposite-strand selection, and oriented nick/release geometry. Validators
  and kernels consume those pure derivations instead of restating them. A
  self-reverse-complement motif is one textual motif-presence match but still
  yields both oriented physical processing events.
- `kernel` owns reusable pure molecular primitives and content identity.
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
- `api` is the package-root design-language operation facade. Thin top-level
  `discovery`, `methods`, and `views` facades expose the three specialized
  competency surfaces without adding derivation logic.
- `cli` adapts user input to the public API and contains no derivations.

`scripts/check_architecture.py` enforces absolute and relative imports, maps the
root `api.py` and `cli.py` modules explicitly, and fails on unknown first-party
layers. The root facade and serialization module are narrow documented
exceptions. The data-only `_facade.py` manifest keeps the package root readable;
the same architecture check requires every public root re-export and manifest
entry to agree. Add an abstraction only when a second real implementation or
consumer makes the seam necessary.

## Current product slices

The public product has four internal semantic surfaces:

1. **Design language.** Exact and symbolic payloads, foldback and basal
   junctions, optional paired stem context, deterministic design derivation,
   and the feature-partitioned `HairpinEncodingInsert`.
2. **Discovery language.** Bounded placement, geometry, precursor, and junction
   queries. Results expose exact candidate identity, `canonical_ordinal`, and
   truthful completion evidence without selecting a candidate.
3. **Method language.** Exact materials and an ordered molecular-state history
   for one named method. The linear-source compiler derives all nicks,
   fragments, selections, pairings, ligation bonds, PCR products, restriction
   products, and cohesive ends.
4. **Provenance and verification.** Separate design and method bundles, strict
   schema replay, byte verification, and an explicit encoding-digest handoff.

Design derivation is non-temporal. Only a named method plan owns production
chronology. A successful design does not imply that a method is available or
feasible, and a method product remains destination-neutral until a caller
checks it against a destination.

Discovery operations answer separate competency questions rather than one
global optimization problem. Canonical order is reproducible interoperability
metadata, not an objective score. Catalog warnings, empirical enzyme behavior,
procurement, application preference, and candidate selection remain caller
policy.

All exact physical pair kinds are deterministic functions of literal bases.
Watson-Crick complements, G:T wobbles, and hard mismatches do not change kind
when a policy accepts or rejects them. Every sequence-bearing method state is
stored 5′→3′ and preserves explicit coordinate lineage.

The [documentation index](docs/index.md) mirrors these sibling surfaces.
Historical architecture choices and their amendments remain in the
[decision index](docs/architecture/decisions/README.md).
