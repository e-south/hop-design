# ADR 0019: Project junction-route views from the selected route

Updated by [ADR 0023](0023-separate-public-facades-by-competency-question.md).

## Context

`build_released_workflow_view` accepts a released state and a separately
evaluated foldback. That low-level composition is useful for resolved design
plans, but it cannot prove that both inputs describe one selected
`HairpinJunctionRouteCandidate`. A caller could pair a valid released state
with an unrelated valid foldback and still obtain a plausible view.

The route candidate also embedded an exact precursor and its geometry without
independently checking that the exact sequence remained inside the geometry's
correlated base domains. The containing search result replayed that
relationship, but an extracted candidate was weaker than its result.

## Decision

Every `HairpinJunctionRouteCandidate` validates its embedded exact precursor
against the embedded released-foldback geometry. Reidentifying an arbitrary
same-length precursor and recomputing its digests is rejected.

`build_hairpin_junction_route_view(route)` is the route-owned QA projection. It
derives the local retained tract, turn, returning arm, and pair observations
from the route's exact released state and geometry, requires that derivation to
reconstruct the active product, and emits the existing `released_workflow`
view contract.

ADR 0023 later promotes the operation through `hop_design.views` while keeping
it out of the package root. Renderers still consume only `WorkflowView` and
perform no molecular derivation.

## Consequences

Routed views derive from the selected route and remain deterministic.
Low-level view composition remains available for other already-resolved plans,
but consumers with a junction route no longer assemble its view from
independent objects.

Caller ranking, route selection, complete-method resolution, and destination
checks remain separate operations.
