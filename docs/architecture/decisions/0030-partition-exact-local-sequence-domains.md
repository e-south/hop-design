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

`NeighborhoodSearchPlan.sequence_partition` may select one of a finite number
of deterministic parts, with `part_count` at least 2 and a zero-based
`part_index`. The number of parts is independent of the per-invocation node,
realization and document limits. For each
canonical exact solution stream, solution ordinal `n` belongs to the part for
which:

\[
n \bmod \mathrm{part\_count}=\mathrm{part\_index}
\]

Filtering occurs after canonical molecular sequence placement and before
realization replay. The partition therefore changes execution and result
identity, but not construction-problem identity or any accepted realization
identity.

Implementations may address the selected canonical ordinals directly. They need
not materialize preceding assignments to reach a later part. Foldback independent
base domains and basal source/adapter domains retain their original enumeration
order; basal addressing accounts for the number of permitted adapter assignments
for each source prefix.

Each result reports completion and feasibility separately for its declared
part. A single part cannot establish whole-domain payload compatibility, so its
payload compatibility is `not_computed`. Partitioning is rejected with
all-member compatibility constraints because that conclusion requires
coordination across the complete domain.

Local feasibility and retained-overhead projections preserve the exact
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

Resumable survey bookkeeping may index these parts, complete construction
witnesses and pending work. The index does not replace molecular replay or the
aggregate checks above. Empty declared parts remain accounted for.

## Consequences

Large exact local searches can remain within the portable result envelope
without hiding missing sequence solutions or changing molecular identity. The
study chooses a part count based on measured result size and retains the full
duplex nick-orientation denominator in its aggregate.

Partitioning is an execution tool, not a score, preference, optimization, or
scientific relaxation. Consumers must not interpret one part as an exhaustive
answer for the unpartitioned request.
