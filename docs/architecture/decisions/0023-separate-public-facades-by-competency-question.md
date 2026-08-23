---
doc_id: hop-adr-0023
title: ADR 0023 - Separate public facades by competency question
intent: Keep the design-language root small while giving discovery, methods, and views explicit supported import surfaces.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-23
doc_type: decision
---

# ADR 0023: Separate public facades by competency question

## Context

The package root accumulated design inputs, bounded-search contracts, named
method states, renderers, and low-level molecular records. That made every
export appear equally central and obscured the distinction between declarative
design, discovery, temporal method realization, and visualization.

## Decision

The package root is the design-language golden path. It exports common design
operations, authored design types, shared coordinates and junction nouns,
primary design results, and operator-facing errors.

Three thin sibling modules own specialized public imports:

- `hop_design.discovery` for bounded queries and their request/result contracts;
- `hop_design.methods` for named methods, molecular states, and method bundles;
- `hop_design.views` for state projections and deterministic rendering.

These facades import their owning models and use cases directly. They contain
no derivation logic. Specialized names are removed from the package root rather
than forwarded through aliases or compatibility shims. Exact allowlist tests
make accidental facade growth or drift fail closed.
The redundant `BasalPairKind` root alias is removed; `JunctionPairKind` is the
single public physical pair-kind name.

## Consequences

Autocomplete and agent routing now mirror HOP's semantic layers. A root import
cannot accidentally present a ligated intermediate as a caller-authored design
type. Discovery, methods, and views remain supported and ergonomic without
promoting internal orchestration modules. This is an intentional alpha breaking
change; retired root import paths are not accepted.
