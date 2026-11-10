# ADR 0005: Canonical junction pair observations

Updated by [ADR 0021](0021-separate-pair-observation-from-policy.md).

## Context

Catalog junctions previously required perfect complementarity while evaluation
models could report wobble and mismatch states. The same noun therefore had two
incompatible physical meanings.

## Decision

`FoldbackJunction` and `BasalJunction` contain ordered
`JunctionPairObservation` values. Each observation records literal bases,
antiparallel indexes, and one `watson_crick`, `gt_wobble`, or `hard_mismatch`
call. Exact catalog defaults and evaluated near matches instantiate the same
types. Feasibility thresholds remain in evaluation and caller policy.

## Consequences

Pair observations cover every aligned position, including mismatches. A map
containing only matches cannot replace these observations. Views and serialized intermediates
consume the canonical junction object. This pre-release correction remains in
the `v1` schemas because no public artifact preceded it.
