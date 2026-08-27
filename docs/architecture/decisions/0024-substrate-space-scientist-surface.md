---
doc_id: hop-adr-0024
title: ADR 0024 - Center first use on bounded substrate spaces
intent: Expose one authored duplex space, one preview, and one verified digital design package without flattening backend competencies.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-27
doc_type: decision
---

# ADR 0024: Center first use on bounded substrate spaces

## Context

HOP's exact design, discovery, method, state, view, and verification contracts
are strong but expose the software lifecycle before a scientist can see the
experiment. A proposed library surface repeated those backend nouns and risked
calling a digital expansion a physical library.

The supported evidence establishes deterministic digital design derivation. It
does not establish pooled construction, molecule-level pairing, QC, activity,
or improvement over another method.

## Decision

The first-use surface exposes one authored `SubstrateSpaceSpec`, one
allocation-free `SubstrateSpacePreview`, and one complete
`HairpinDesignSet`. The public facade is `hop_design.spaces`; its exact
allowlist is separate from the package root.

The caller authors one segmented payload arm. HOP derives the opposite arm.
V1 supports exhaustive compilation only. A valid space above its explicit
member bound is `blocked`, not infeasible or truncated. Compilation publishes
no authoritative partial set.

Each unique member remains an unchanged, verified `HopBundle`. The collection
authority lives below `bundle/`; the source YAML, sequence exports, and offline
HTML review are regenerable projections outside identity. The canonical
molecular specification records only the ordered per-position DNA domains and
the resolved versioned hairpin defaults reference. Display names, descriptive
context, segment labels, equivalent segment boundaries, and allocation bounds
are excluded from member and collection identity.

The design-set manifest uses `hop.hairpin-design-set/v2`. Member identifiers
derive from the canonical molecular-space digest and exact variable assignment;
the collection identifier derives from the complete manifest without embedding
a display name. No compatibility reader is retained for the prerelease schema.

Compilation verifies members and collection before atomically committing a
new destination. Standalone verification is a handoff operation rather than a
required extra step in the primary define, preview, compile journey.

The surface uses `design set` and `design package` for digital output.
`physical library`, `constructed`, `QC-passed`, and `assay-ready` remain terms
for separately owned experimental evidence.

## Consequences

The scientist can understand the declared sequence space, exact size, paired
arm, output sequences, and evidence boundary without learning HOP's backend
ontology. Discovery retains `complete`, `infeasible`, and `truncated` for its
different competency questions. Named methods, molecular states, provenance,
and typed views remain available through progressive disclosure.

The public tracer contains three fully variable positions and therefore 64
exact members. This is an example and regression fixture, not an architectural
limit. Sampled sets, pooled method assessment, QC attachments, assay data, and
a browser authoring application require separate evidence and decisions.
