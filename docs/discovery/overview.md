# Discovery and selection

Use four operations to move from requirements to saved results that HOP can
reproduce from their recorded inputs:

1. **Evaluate** a fully declared component.
2. **Discover** compatible sequences and cut positions within declared choices.
3. **Select** a candidate using caller-owned experimental or procurement policy.
4. **Compile** selected components or a named method into plans and output files.

The [two-region envelope example](../../examples/local-envelope/README.md)
derives local contact lengths from geometry and varies independent basal and
foldback budgets. It shows how to count local results, retain incomplete search
coverage, and distinguish a union across variable sources from one fixed source.

## Payload-centered local construction discovery

A local search resolves one junction. Its exact solutions become inputs to the
complete construction check, which combines the junctions, resolves materials
and derives the requested product.

A local construction request fixes the final payload, route family, requested
endpoint, one finite foldback or basal geometry domain, and a maximum retained
non-payload overhead: construction sequence retained outside the payload. HOP
examines admissible geometry in increasing absolute overhead order, subject to
the declared search limits. Each exact local solution, called a realization,
preserves both the declared domain and its achieved geometry.

HOP reports retained overhead for each realization and leaves geometry selection
to the caller. Completion and feasibility are reported separately:

- `complete` means the declared finite task was exhausted;
- `stopped_by_policy` means an explicit result quota ended an otherwise valid
  search;
- `truncated` means a resource or execution bound prevented the requested
  coverage; and
- feasibility is `feasible`, `infeasible`, or `unknown` according to what that
  coverage establishes.

For each overhead level, HOP records examined candidates, accepted realizations,
rejections, and observed failure categories. A partial level appears only when
coverage is incomplete. A local construction projection renders the same typed
result as neutral JSON, CSV, or SVG without selecting a realization or
recomputing molecular state. To obtain complete materials and an endpoint
product, compose the local realizations through complete construction.

An unchanged payload can itself exclude a foldback enzyme program: an extra
actionable site wholly inside that duplex cannot be repaired by varying the
construction region. HOP checks this using the same recognition, orientation,
substrate, and cut rules as exact reaction replay. Such a whole-program exclusion
counts as one rejected evaluation. Evaluation counts therefore do not supply a
raw sequence-space denominator.

## Foldback geometry

A foldback domain declares finite nick-boundary, strand, annealing-arm, and loop
possibilities. HOP orders those possibilities by retained endpoint overhead,
then materializes exact precursor sequences within caller-authored constraints.

Recognition-motif length is not automatically an added-nucleotide cost. Motif
positions may overlap the paired tract or the declared turn. The relevant
measure is how far a placed footprint extends beyond sequence already available
to the design, reported through required precursor and turn lengths.

Discovery proves only the declared finite domain. A minimum-overhead statement
requires every lower applicable level to be complete at the same scope.

## Symbolic domains

### Search a basal cohesive end or pin it to a destination

The future release's `cohesive_end_sequence` accepts either exact DNA or an
IUPAC pattern. For example, `ATGC` pins one end; `ATNN` allows 16 exact ends;
`NNNN` allows all 256 four-base ends. The search enumerates exact ends within
that domain. See the
[construction guide](../guides/compile-construction.md) for the full request.

The source must satisfy both recognition motifs when `recognition_material`
is `source_duplex`. The adapter can differ from the displaced strand at
positions allowed by `pairing_constraints`. Those literal matches, wobbles,
and mismatches remain visible in each solution. The nickase must recognize
the source when it acts; later cleavage must recognize the copied product
when it acts. A permitted adapter mismatch does not waive either requirement.

Local discovery can leave the full association requirement open by setting
`minimum_adapter_annealing_nt` explicitly to `null`. The exact proximal pairs
remain resolved; the full required length, distal completion count, and
full-span mismatch fraction remain unknown. The unresolved distal region is
not a zero-length arm, and the local segment does not establish the full
annealing requirement. Complete construction requires an explicit association
requirement and rejects an
unresolved parent as an input error before evaluating combinations. Discovery
can be repeated with a chosen requirement without changing its local sequence
search; the saved result retains that requirement for composition.

Each returned target and enzyme action has one exact end. Complete construction
selects an exact endpoint from the allowed domain and rejects a selected local
end that disagrees. Enumeration uses offset then A/C/G/T end order, not an
experimental ranking. The offset-by-end domain is limited to 100,000 exact
targets before allocation; the request's evaluation limits still govern search
completion. Minimum-overhead tables retain separate actions for different exact
ends, even when the same enzyme realizes them.

Every future release declares `payload_end_offset_bp`: the number of non-payload
paired positions between the payload edge and the near edge of the protruding
end. It is independent of `nick_offsets_nt`. Zero places the end beside the
payload and still retains the declared overhang length. In the payload-forward
source frame, an end of length `k` at offset `e` occupies `[-e-k, -e)` and a nick
of displacement `n` has boundary `-n`. HOP transforms each oriented action's two
cuts into that frame; the overhang sequence remains in its own protruding
strand's 5-prime direction.

Source-supplied end bases and adapter-supplied end bases follow their actual
interval overlaps. Unspecified source bases remain searchable. End bases beyond
the constrained local adapter span remain explicit completion obligations, not
invented local sequence. Complete construction requires the same declared gap
and checks it against both actual strand cuts. An omitted offset is invalid;
current requests do not infer zero from an earlier schema.

### Preserve payload domains

An IUPAC symbol is a set of possible bases, not a wildcard character. HOP uses
set intersection to distinguish guaranteed, possible, and absent motif
presence. Exact precursor searches calculate their candidate-space cardinality
before enumeration and preserve dependencies between paired positions. For
example, choosing one base constrains its paired partner; those two choices
cannot be counted as independent.

Avoid an unqualified “degeneracy cost.” Neutral measurements include:

- the number of authored positions narrowed by a process footprint;
- the resolved domain at each position; and
- the change in exact sequence-space cardinality.

Synthesis cost, preferred diversity, and application value belong to the
caller.

## Ordering is not recommendation

Candidate order is deterministic so two consumers can replay the same bounded
result. Basal and concrete precursor searches use literal content order;
geometry searches use stable identifiers and declared coordinate relations.
Measured GC content, homopolymer length, extra-site counts, or M/W/X profiles
do not silently determine the prefix returned under a hit budget.

`canonical_ordinal` records a reproducible position in HOP's neutral order.
Optimization would need a named objective, reported measurements,
and deterministic tie-breaking. Save the caller's selection rule and selected
candidate identity.

## What site placement proves

Site placement checks the motif, orientation, and cut coordinates against the
modeled substrate. Catalog entries can carry warning codes; those codes do not
change discovery admission. Callers apply and preserve their own versioned
protocol rules. For enzyme-specific flanking-base requirements, consult [NEB's
cleavage-close-to-ends guidance](https://www.neb.com/tools-and-resources/usage-guidelines/cleavage-close-to-the-end-of-dna-fragments).

An advisory contract would need to identify the agent, applicable context,
evidence, and severity.

The [mechanics reference map](../reference/mechanics-api.md) routes each bounded search
and its completion evidence.
