---
doc_id: hop-adr-0008
title: ADR 0008 - Inherited component assembly
intent: Separate component composition from processing-route discovery and provenance.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-20
doc_type: decision
amended_by: hop-adr-0020
---

# ADR 0008: Inherited component assembly

> Amended by [ADR 0020](0020-separate-design-derivation-from-method-chronology.md):
> the historical `resolved_events` and `component_assembly` variants were
> replaced by strict design-derivation contracts with no ordered method history.
> [ADR 0022](0022-make-boundaries-order-and-cohesive-ends-explicit.md) later
> removed the redundant generic foldback `nick_boundary`; the retained-tract
> span now owns that topology coordinate without implying a nick.

## Context

Existing or externally designed hairpins may supply literal foldback and basal
components without a recoverable enzyme route. The components can still have
well-defined sequence, topology, pairing, and lineage. Treating an absent route
as molecular infeasibility would conflate three independent claims:

1. the component is physically represented;
2. a search operation generated or found it;
3. a processing route is known and selected.

Historical component handles and biological parent families can also differ.
Replacing either identifier with the other would discard provenance.

## Decision

`ResolvedHopSpec` supports two explicit outcomes:

- a `resolved_events` plan when `BasalDesignRequest.terminal_nick` is present;
- a `component_assembly` plan when the terminal nick and release event are
  absent.

Component assembly evaluates the supplied foldback and basal components,
derives the paired payload, composes the five-part insert, and emits a verified
bundle. Its state graph contains foldback, basal pairing, and insert assembly.
It does not assert that HOP discovered the components or that a nicking or
release route exists. Route-neutral foldback and basal views avoid invented
pre/post-processing states.

At the time of this decision, `FoldbackEvaluationRequest.nick_boundary`
duplicated the start of the retained tract without establishing that a nicking
operation occurred. [ADR 0022](0022-make-boundaries-order-and-cohesive-ends-explicit.md)
removed that field; `retained_tract_span.start` is now the sole route-neutral
foldback origin.

A release event still requires a terminal nick and therefore cannot enter
component assembly. Caller systems own historical lineage and application
meaning and may link those records through neutral external references.

For compatibility, `processing_route_ref` remains the field that locks the
selected implementation behavior. A component assembly uses an assembly
reference there; the `component_assembly` discriminator carries the narrower
claim. Renaming the field is deferred until a future schema version justifies
the migration cost.

## Compatibility

Existing specs retain their terminal nick and produce the same
`resolved_events` plan. The optional terminal-nick input and new plan-route
discriminator are additive on the `0.1.0a1` development line. Consumers must
recognize `component_assembly` before accepting bundles that use it.

## Consequences

Externally inherited components can pass molecular and composition parity
without guessed enzymes or strands. Route discovery remains a separate,
optional operation. A negative catalog search may be recorded as evidence, but
it does not invalidate a component assembly whose route was never asserted.
