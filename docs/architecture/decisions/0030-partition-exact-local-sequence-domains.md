---
doc_id: hop-adr-0030
title: ADR 0030 - Partition exact local sequence domains without changing molecular identity
intent: Keep large exhaustive local searches portable while preserving the complete declared sequence space.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
journey:
  - discover
  - verify
---

# ADR 0030: Partition exact local sequence domains without changing molecular identity

## Context

An exact foldback or basal geometry can admit enough sequence solutions that
one replayable result exceeds the portable 64 MiB authority limit even though
the declared search is finite. Raising the byte limit would couple portability
to one study. Truncating the search would change an exhaustive scientific
question into an unresolved one.

Nick strand is part of the duplex molecular solution and is not an acceptable
proxy for dividing or reducing this sequence space. An unconstrained foldback
request must continue to examine both physically valid nick orientations.

## Decision

`EnumerationPolicy.sequence_partition` may select one of 2 through 256
deterministic parts using `part_count` and zero-based `part_index`. For each
canonical exact solution stream, solution ordinal `n` belongs to the part for
which:

\[
n \bmod \mathrm{part\_count}=\mathrm{part\_index}
\]

Filtering occurs after canonical molecular sequence placement and before
realization replay. The partition therefore changes execution and result
identity, but not construction-problem identity or any accepted realization
identity.

Each result is complete, infeasible, or truncated for its declared part. A
single part cannot establish whole-domain payload compatibility, so its payload
compatibility is `not_computed`. Partitioning is rejected with
`first_feasible_shell` stopping and with all-member compatibility constraints,
because those conclusions require coordination across the complete domain.

Local feasibility and relaxation projections preserve the exact
`sequence_partition`. Their JSON and CSV forms expose its part count and
zero-based part index. Their SVG form describes only that part and cannot use
whole-domain exhaustive language, including when the part is complete but
infeasible. Projection schemas were incremented when this scope became part of
their canonical typed relation; no compatibility aliases reinterpret earlier
projection bytes.

HOP does not create a partition-family authority. An owning study may establish
exhaustive aggregate coverage only when it records:

- one common problem identity and part count;
- every ordered part index from zero through `part_count - 1`;
- replay-verified result identities and exact bytes;
- no truncated part;
- pairwise-disjoint realization identities; and
- summed candidate, rejection, and failure accounting.

Presence of every part proves gap-free canonical candidate coverage. Replay and
disjoint realization identities preserve accepted-member integrity.

## Consequences

Large exact local searches can remain within the portable result envelope
without hiding missing sequence solutions or changing molecular identity. The
study chooses a part count based on measured result size and retains the full
duplex nick-orientation denominator in its aggregate.

Partitioning is an execution tool, not a score, preference, optimization, or
scientific relaxation. Consumers must not interpret one part as an exhaustive
answer for the unpartitioned request.
