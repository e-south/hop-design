---
doc_id: hop-adr-0018
title: ADR 0018 - Join hairpin-junction processing on one strand
intent: Define the bounded physical handoff between an exact released foldback and an exact basal-processing route.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-22
doc_type: decision
amended_by: hop-adr-0023
---

# ADR 0018: Join hairpin-junction processing on one strand

## Context

Released-foldback precursor search selects an exact processable precursor and
its nick/release geometry. Basal-processing route search selects an exact basal
pair, retained scar, terminal nick, and surviving strand. Each result is
independently replayable, but neither proves that the two junction processes
preserve the same continuous molecular strand.

Combining the results by agent name would be insufficient. Two end processes
can use different release agents, while two routes that happen to name the same
agent can still retain opposite strands. Re-enumerating either upstream search
would also create a second authority for candidate identity and completeness.

## Decision

HOP provides `search_hairpin_junction_routes` as a bounded join of one typed
`ReleasedFoldbackPrecursorSearchResult` and one typed
`BasalProcessingRouteSearchResult`.

For each examined Cartesian pair, HOP:

- projects the exact precursor through its selected nick and release cuts;
- verifies that the released state reuses the selected geometry, span, and
  active-oriented nick boundary;
- compares the released active strand with the strand that survives basal
  terminal nicking; and
- returns a route only when those strand identities agree.

`continuous_strand_mismatch` is the stable incompatibility reason. The route
embeds the exact precursor, selected geometry, released molecular state, basal
route, and content identity. It preserves the two release-agent identities and
orientations independently. HOP does not require them to match and does not
prefer a one-enzyme or multi-enzyme route.

The result reports upstream precursor and basal-route incompleteness separately
from its own node and hit budgets. `complete` describes exhaustive evaluation
of the available upstream cross-product; it does not mean that a wet-lab method
or destination assembly has been selected.

ADR 0023 later moved this operation and its public contracts from the package
root to `hop_design.discovery`; the molecular decision is unchanged.

Route-owned QA projection is defined separately by
[ADR 0019](0019-project-junction-route-views-from-the-route.md).

## Consequences

The two hairpin-junction processing surfaces now share one explicit molecular
continuity contract. Callers can compare or filter enzyme sets after receiving
physically coherent routes without changing HOP identity or order.

This result does not choose a payload, construct a full source molecule,
resolve method materials, prove a complete production method, or claim
destination readiness. Live-catalog candidate parity, routed QA views, and
downstream cutover remain separate gates.
