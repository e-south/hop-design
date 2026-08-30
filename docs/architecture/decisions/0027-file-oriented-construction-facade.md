---
doc_id: hop-adr-0027
title: ADR 0027 - Compile construction from strict files behind a narrow facade
intent: Give external callers one replayable construction entrypoint without exporting the internal molecular ontology.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
amended_by: hop-adr-0028
---

# ADR 0027: Compile construction from strict files behind a narrow facade

> Amended by [ADR 0028](0028-separate-foldback-boundary-from-nick-position.md):
> the active construction source is v2 and uses an explicit nick offset within
> the retained foldback arm.

## Context

Payload-centered construction discovery now produces exact local authorities,
complete route realizations, portable bundles, and neutral scientific
projections. Those competencies were reachable only through internal model and
design modules. An external caller would have needed to construct embedded
design authorities and connect local result identifiers by hand.

Publishing those internal request, result, molecular-state, and manifest models
would make the complete ontology a supported user surface. It would also let a
source document claim a design authority that HOP had not independently loaded
and verified.

## Decision

`hop_design.construction` is the file-oriented construction facade. The caller
provides one strict `hop.construction-source/v2` JSON or YAML file and one
separate verified design-bundle path. HOP loads the design authority, discovers
and verifies the declared foldback and optional basal neighborhoods, derives
the complete request, composes the route, and returns an opaque
`ConstructionCompilation` receipt.

The source document owns local requests, endpoint-dependent exact materials,
whole-route constraints, and finite enumeration policy. It cannot author a
design authority, result identifier, realization identifier, projection
choice, output path, timestamp, or environment record. Direct, PCR, and
clone-ready endpoints have fail-closed structural requirements.

The exact public allowlist is:

- `ConstructionCompilation`;
- `VerifiedConstructionBundle`;
- `ConstructionProjection`;
- `compile_construction`;
- `load_verified_construction_bundle`;
- the foldback, basal, relaxation, complete-summary, and explicitly selected
  trajectory projection operations.

Receipts expose only scalar identity and accounting plus create-only writing.
Projection packets expose deterministic JSON, optional CSV, and SVG bytes.
Raw Pydantic source, result, projection, molecular-state, and bundle-manifest
models remain internal. Loading a portable construction bundle performs both
integrity and semantic replay, so the facade does not add a redundant verify
verb.

## Consequences

Research Studies and other callers can use the same installed public interface
without copying HOP models or importing private modules. A projection must be
requested from an opaque verified receipt; trajectory projection additionally
requires one exact accepted realization identity and never auto-selects an
exemplar.

The source compiler may report complete, infeasible, or truncated discovery.
None of those digital states establishes physical construction, QC,
destination compatibility, biological activity, or route performance. This is
an intentional prerelease public-surface addition with no compatibility alias
for internal import paths.
