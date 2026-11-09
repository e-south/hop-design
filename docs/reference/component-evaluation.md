# Component evaluation and released-state projection

These operations inspect supplied junctions and cuts. Evaluators report the
pairing and geometry of one input; searches enumerate permitted alternatives
under explicit limits. A released-state projection derives the strands that
remain after the supplied cuts.

## Foldback junction

`evaluate_foldback(FoldbackEvaluationRequest)` derives the canonical junction,
source and effective turns, pair observations, Watson–Crick runs, and added
nucleotide count. `retained_tract_span.start` declares the foldback origin;
nick geometry is supplied separately. A cap-only junction may have zero
retained and returning bases while preserving a nonempty turn.

`search_foldback_arms(FoldbackSearchRequest, limits=...)` requires a nonempty
retained tract and reports exact cardinality, nodes, hits, and completion.
Diagnostics `HOP-FOLD-001` through `HOP-FOLD-006` cover pair policy, protected
regions, run bounds, added nucleotides, and turn length. G:T is always observed
as `gt_wobble`; policy decides whether it is accepted.

## Basal junction

`evaluate_basal_pairing(BasalPairingRequest, constraints=...)` observes four
S3/S2/S1/S0 pairs as `watson_crick`, `gt_wobble`, or `hard_mismatch`. The
caller-supplied `BasalConstraintProfile` separately returns `active`, `reserve`,
or `reject`. Reserve acceptance must be explicit.

`pair_support_index` and `pair_disruption_index` summarize the observed pairs
using the dimensionless `pair-count-weighted@1` heuristic.

## Paired stem extension

`evaluate_paired_stem_extension(PairedStemExtensionRequest)` observes every
position in two equal-length literal arms. Use it to describe added pairing
outside the payload. This keeps the four-position terminal basal profile at its
defined size and leaves the paired payload derived from the authored arm.

## Released-strand projection

`project_released_strand_state(ReleaseProjectionRequest)` accepts an exact
precursor, origin, strand-specific nick, duplex cut, optional release-site span,
route, and constraints. A successful projection contains active and retained
strands, spans, the active-product nick boundary, and per-base lineage.

Stored molecular sequences are 5′→3′. Bottom-active products are reverse
complements with descending precursor indexes. Route and nick strand must
agree; invalid geometry fails at construction. Diagnostics `HOP-PROC-001`
through `HOP-PROC-004` describe expected cut and release infeasibility.

## Compiler integration

`ResolvedHopSpec` supplies explicit foldback and basal requests plus optional
terminal-nick and release geometry. `check` aggregates independent diagnostics;
`compile` refuses errors and emits a feature-partitioned encoding, evaluated
intermediates, and typed views.

Compilation derives the design from the supplied components. Release geometry
requires a terminal nick whose active product equals the foldback precursor;
otherwise `HOP-ROUTE-001` reports the mismatch.
