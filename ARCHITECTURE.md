---
doc_id: hop-architecture
title: HOP Design architecture
intent: Define ownership, dependency direction, and module boundaries.
audience:
  - maintainers
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
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

The accepted construction-discovery graph is payload-first:

```text
final-payload specification + route family + requested endpoint
  |-> foldback local realizations
  |-> basal local realizations
  |-> source-partition realizations
  `-> endpoint materialization
                  |
                  v
       staged whole-route composition
                  |
                  v
       exact endpoint products and reversible projections
```

Local junction discovery owns only the sequence and reaction geometry at one
payload boundary. Source-partition discovery owns provisioned nickase subsets,
all actionable sites, denatured fragments, length selection, and the exact
required survivor relation. PCR handles, primer binding, Type IIS release, and
other endpoint periphery are route-materialization concerns. A study may run
these bounded competencies independently; complete composition may claim only
the authorities explicitly present in its request.

The public construction entrypoint binds that spine to files without exposing
its model graph:

```text
strict construction source + separately verified HopBundle
  -> verified local authorities
  -> verified complete construction
  -> opaque receipt
  -> portable ConstructionBundle or neutral projection packet
```

The source owns requests, exact materials, constraints, and bounds. The design
bundle owns design identity and encoding. The construction bundle embeds the
unchanged design authority needed for replay and owns only the complete-route
result and its inventory.

Final-payload coordinates are shared authority. Source coordinates and source
segmentation belong to the selected route family. The current linear-source
family may use one contiguous source interval without making that layout a
global payload invariant.

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
  method request resolves into modeled molecular states and products; it does
  not redefine design identity or claim destination readiness, physical
  construction, or recovery.
- `api` is the package-root design-language operation facade. Thin top-level
  `spaces`, `construction`, `discovery`, `methods`, and `views` facades expose
  the scientist-facing workflow and specialized competency surfaces without
  adding derivation logic. `spaces` authors a bounded sequence space and
  returns existing member authorities rather than redefining their anatomy.
  `construction` accepts strict files plus a separately verified design bundle
  and returns opaque receipts rather than exporting the construction ontology.
- `cli` adapts user input to the public API and contains no derivations.

Construction discovery reuses the specialist discovery, molecular-state,
method, and view layers. Its shared local-neighborhood contract must not enter
the seven-name `hop_design.spaces` facade or inflate the package root. Foldback
and basal targets share result, completeness, relaxation, and identity
semantics while retaining family-specific geometry. Source partitioning is a
sibling authority rather than a basal-neighborhood subtype. Its public receipt
is exposed only through `hop_design.construction`.

`scripts/check_architecture.py` enforces absolute and relative imports, maps the
root `api.py` and `cli.py` modules explicitly, and fails on unknown first-party
layers. The root facade and serialization module are narrow documented
exceptions. The data-only `_facade.py` manifest keeps the package root readable;
the same architecture check requires every public root re-export and manifest
entry to agree. Add an abstraction only when a second real implementation or
consumer makes the seam necessary.

## Current product slices

The public product has four internal semantic surfaces and one first-use
workflow:

0. **Scientist surface.** One bounded substrate-space specification, symbolic
   preview, complete digital design set, and offline review. It composes the
   design and verification surfaces without making method or experiment claims.

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
4. **Provenance and verification.** Distinct design, construction, and method
   bundle claims; strict schema replay; byte verification; embedded design
   authority for construction replay; and an explicit design-method encoding-
   digest handoff.

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

Construction-route chronology is an ordered list of reaction stages. All
concurrent operations in one stage resolve against the same pre-stage state;
site validity depends on molecular availability in that stage. Compactness is
an endpoint projection over retained non-payload sequence, not total source
length. Geometry and final-product grouping remain reversible projections over
exact realization authorities.

For a PCR-bearing linear-source route, the retained source prefix may extend
beyond the local basal pairing span. Its source-return arm is the reverse
complement of that complete prefix and is removed after basal nicking. The
ligation adapter is a separate exact material paired only through the declared
basal profile. The verified design may therefore occupy a nonzero subspan of
the PCR product, with outer source periphery and primer handles remaining
explicit.

HOP may emit neutral tidy data and diagram-ready molecular projections.
Research Studies owns scientific runs, observations, interpretation, and asset
promotion. manufold owns accepted evidence snapshots, manuscript claims, and
figure composition. Neither consumer may drive HOP's molecular semantics.

The [documentation index](docs/index.md) mirrors these sibling surfaces.
Historical architecture choices and their amendments remain in the
[decision index](docs/architecture/decisions/README.md).
