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
last_verified: 2026-08-31
doc_type: decision
amended_by: hop-adr-0028
---

# ADR 0027: Compile construction from strict files behind a narrow facade

> [ADR 0028](0028-separate-foldback-boundary-from-nick-position.md) makes
> duplex foldback nick orientation explicit. [ADR 0033](0033-close-linear-source-material-dependencies.md)
> closes the source-ssDNA preparation dependency in the active v5 construction
> source.

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
provides one strict `hop.construction-source/v5` JSON or YAML file and one
separate verified design-bundle path. HOP loads the design authority, discovers
and verifies the declared foldback and optional basal neighborhoods, derives
the source ssDNA and source-preparation primers under their declared policies,
produces the exact source duplex, optionally binds one selected replay-verified
source partition, resolves PCR endpoint auxiliaries under their declared
policies, composes the route, and returns an opaque `ConstructionCompilation`
receipt.

The source document owns local requests, source-preparation policy,
endpoint-dependent auxiliary-resolution policy, oriented endpoint release,
whole-route constraints, and finite enumeration policy. Source preparation
uses one source ssDNA and two source-preparation primers to derive the exact
duplex that enters downstream construction. Endpoint PCR primers remain
separate auxiliary materials and appear only for PCR-bearing endpoints. Their
adapter and primer policies are explicitly `derive`, `constrain`, or `fixed`.
Derived and constrained endpoint primers must bind invariant non-payload
construction sequence, and caller-authored handles remain explicit rather than
being selected through an implicit score. The source cannot author a design
authority, result identifier, realization
identifier, projection choice, output path, timestamp, or environment record.
Direct, PCR, and clone-ready endpoints have fail-closed structural requirements.

The exact public allowlist is:

- `ConstructionCompilation`;
- `ConstructionProjection`;
- `ConstructionSelection`;
- `LocalNeighborhoodDiscovery`;
- `SourcePartitionDiscovery`;
- `VerifiedConstructionBundle`;
- `compile_construction`;
- `compile_construction_from_local_realizations`;
- `compile_design_from_local_realizations`;
- `discover_local_neighborhood`;
- `discover_source_partition`;
- `load_verified_construction_bundle`;
- `load_construction_selection`;
- `load_verified_local_neighborhood`;
- `load_verified_source_partition`;
- `project_basal_feasibility`;
- `project_complete_construction_summary`;
- `project_construction_navigation`;
- `project_construction_trajectory`;
- `project_foldback_feasibility`; and
- `project_relaxation_frontier`; and
- `select_construction_realization`.

Receipts expose only scalar identity and accounting plus create-only writing.
Projection packets expose deterministic JSON, optional CSV, and SVG bytes.
Selection references expose only the source result identity, one accepted
materialized-realization identity, and canonical JSON. They remain
non-authoritative: creating or loading one requires a verified construction
receipt, and loading cross-checks both identities against that receipt.
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

The projection operations remain the reversible navigation data surface. The
`hop-design construction` CLI consumes those projections to summarize, group,
filter, explicitly sort, inspect, and select exact realizations without changing
result authority or introducing a hidden rank. Its row limit affects display
only and does not alter search status, accounting, or membership.

An explicit selection writes one create-only JSON file at the caller-supplied
path. It does not mutate, subset, reseal, or supersede the complete result, and
it cannot be reopened without the verified result that establishes membership.

Standalone local-neighborhood discovery returns one replay-verified family
receipt. It establishes only the declared foldback or basal neighborhood and
cannot be interpreted as a complete-route authority.

For a PCR-bearing endpoint, a caller may explicitly select one realization
from each verified local receipt and compile their exact molecular junctions
into a route-neutral design authority. The selection operation returns the
existing `Compilation` type. Search-result identities, execution bounds, and
reaction chronology do not enter the design specification or plan identity.

The source compiler may report complete, infeasible, or truncated discovery.
None of those digital states establishes physical construction, QC,
destination compatibility, biological activity, or route performance. This is
an intentional prerelease public-surface addition with no compatibility alias
for internal import paths.
