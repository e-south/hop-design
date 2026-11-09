# ADR 0001: Standalone package boundary

## Context

HOP behavior has predecessors embedded in larger design and study workflows.
The intended endpoint is an independently installable public utility that those
workflows can consume without owning HOP.

## Decision

HOP Design is a standalone repository, `hop-design` distribution,
`hop_design` import package, and `hop-design` CLI. It re-specifies the minimal
kernel it needs and imports no caller repository at runtime.

## Alternatives

Nesting inside a monorepo would reuse tooling but preserve ownership and release
coupling. Wrapping a predecessor package would avoid an initial port but create
a permanent dependency on unrelated workspace and study concepts.

## Consequences and reversal cost

HOP needs its own CI, docs, release discipline, and parity fixtures. Downstream
consumers migrate only after checks establish that the required outputs are equal.
Reversing this decision later would be costly because public imports and artifact schemas depend on the owner
boundary.
