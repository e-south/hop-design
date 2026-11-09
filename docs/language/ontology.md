# HOP Design ontology

## Describe the molecule before its construction role

Start with the supplied stem. The foldback neighborhood closes one end; the
basal neighborhood supports adapter association at the other. These are roles
in the preparation, while stem, loop, tail and overhang describe physical
features in a named molecular state.

| Feature | Where to locate it | Construction interpretation |
| --- | --- | --- |
| Paired stem | Opposing positions on the folded strand | The supplied experimental sequence and its copied complement; added pairing is measured separately |
| Loop | Unpaired bases joining the two stem arms | The closing sequence; its size follows its exact word |
| Tail | Unpaired sequence at a strand terminus | May supply primer homology, be removed, or contribute to a later product; ancestry determines which |
| Noncanonical contact | Two recorded interacting positions | An explicitly permitted mismatch or wobble; it is not an unpaired tail |
| Overhang | Protruding sequence on the released duplex | A receiving interface, with its word read 5′→3′ on that strand |

A nucleotide may have several construction roles across processing states.
Primer homology upstream of the basal region is not synonymous with basal
pairing. An annealing minimum is a requirement; the achieved paired span is a
measurement. A nick is a strand boundary; a recognition footprint is an interval.
The [parameter registry](../reference/molecular-parameters.md) supplies units,
measurement boundaries and dependencies, including `R = A − D` and loop length
from the loop word. Equivalent measurements are counted once.

This separation of structural feature from contextual annotation follows the
useful representational principle illustrated by
[bpRNA](https://doi.org/10.1093/nar/gky285). HOP derives its contacts from the
construction's molecular states.

The atlas descriptor `x` is a typed record of these measured features, retained
regional sequences/contacts and receiving interfaces. Nominal contact codes
identify base pairs and contact classes; their numerical differences have no
meaning. A captured comparison policy supplies the scales and block weights
used to calculate molecular dissimilarity. UMAP places its neighbors. The
invariant stem, duplicated measurements and preparation identifiers do not
create extra distance dimensions. Methods remain available for inspection and
further search. Each selectable point has a complete construction witness; plot
position comes from the comparison policy.

## Construction search and its molecular meaning

One request defines a permitted molecular domain. Search derives necessary
relations, proposes assignments and asks the complete compiler to verify their
preparations. Conditional plots, stage-resolved sequence views and oligo handoff
project those verified records; none introduces another molecular authority.

| Term | Biological or computational meaning |
| --- | --- |
| Permitted domain | Authored stem, joint interface choices, geometry, methods and material permissions; a computing quota does not narrow it |
| Necessary relation | Joint assignments that satisfy the translated constraints, retaining correlated bases; membership alone does not establish a complete route |
| Local neighborhood | Foldback or basal construction region with its own sequence, geometry and processing constraints; local solutions are reusable inputs to complete construction checks |
| Candidate assignment | A particular geometry, method and sequence choice to evaluate through the complete construction |
| Auxiliary completion | A choice of additional material bases under explicit permissions; some may affect retained sequence and cannot be treated as interchangeable |
| Product | The exact molecule at a named processing stage, with sequence, contacts and terminal chemistry |
| Preparation | A verified modeled route and exact materials producing the requested product; different preparations can produce the same product |
| Processing state | A recorded molecular state linked by copying, cleavage, association or joining; search traversal order is not a physical time course |
| Selection | A bound reference to a verified preparation; a branch/page address alone is not molecular identity |

For `paired_scaffold_completions`, consequential paired/retained sequence remains
explicit while other permitted handle bases are completed as needed. This does
not enumerate every exact unpaired hairpin or material variant. Unknown
propagation frames retain ordinary evaluation rather than becoming exclusions.

Material policies answer a separate question from the diversity objective:
`fixed` requires the exact material; `constrain` permits assignments within the
declared domain; `derive` constructs a material from the selected route and its
requirements. A `constrain` sequence containing only A/C/G/T still fixes every
base. IUPAC alternatives or a length range create a searchable domain. Auxiliary
completion must satisfy required homology, chemistry, recognition sites and
whole-route checks. It cannot repair a contradiction by changing a fixed material.

Foldback and basal domains are solved separately. Combining them still requires
the complete compiler: local validity is distinct from verified composability.
See [interface surveys](../guides/survey-interfaces.md) and
[their contract](../architecture/decisions/0052-resumable-interface-surveys.md).

## Design and method authorities

Design and method products are sibling authorities:

```text
DesignSpec -> DesignDerivation -> HairpinEncodingInsert -> HopBundle
                                      |
                                      | encoding-digest equality
                                      |
MethodRequest -> method states -> RestrictionDigestProduct -> MethodBundle

RestrictionDigestProduct + caller destination -> AssemblyFragment
```

Discovery proposes compatible geometry. Caller policy selects among candidates.
Views and files project derived state; they do not become a second authority.
The cross-bundle equality is a checked handoff, not an invariant of every
independently compiled pair. It holds when the method request supplies
`expected_hairpin_encoding`, or when the consumer performs the same exact
digest comparison before associating the products.

## Payload-centered construction vocabulary

A **basal association** is the recorded source–adapter contact region, with literal
paired positions and permitted contact classes. Unpaired source-side and
adapter-side handles lie beyond that association. Primer homology is a material
function at a declared stage; it may overlap another function in the same bases.

A **hairpin core** is the route-neutral design sequence and its supplied-stem,
foldback and basal features. For a released-insert construction, its projection
is anchored in the PCR parent. The **released insert** is the exact pair of strands
retained by end-generating cuts. Its union need not equal that core: outer
construction bases may be removed and other construction bases retained. The
protected interval containing both supplied-stem copies and foldback remains
intact on both strands. End words and paired end-to-stem distances describe this
released state; they do not describe the hairpin handles.


The accepted construction authority is the user-defined duplex payload in
final-product coordinates. Its reference strand is authored 5-prime to
3-prime, its aligned complement is derived, and its basal and foldback
boundaries are explicit. A route family owns the mapping from these positions
to one or more source-material segments. `linear_source/v1` is the current
family; contiguous source encoding is its property, not a universal payload
property.

An endpoint names the requested molecular product. `ssdna_hairpin` ends at the
closed single-stranded hairpin, `hairpin_pcr_duplex` adds adapter capture and
PCR, and `clone_ready_duplex` adds declared end-generating cleavage and exact
cohesive ends. Endpoint choice determines required neighborhoods, materials,
operations, and states.

A local-neighborhood request is the shared envelope for a foldback or basal
construction question. It combines final payload, route family, endpoint,
family-specific target geometry, required constraints, design preferences,
caller-provisioned enzymes, explicit relaxation, and finite enumeration. Its
result preserves requested and achieved geometry, relaxation shell, every
exact realization, rejection accounting, completion evidence, and reversible
projections. Large exact sequence domains may be divided into deterministic,
disjoint execution parts without changing the molecular problem or realization
identities. One part does not establish whole-domain payload compatibility.

A foldback target is described by `junction_offset_nt`, `loop_length_nt`, and
`annealing_arm_length_bp`. A basal target describes endpoint-dependent nick
geometry, an exact ligation-proximal-outward pairing state, and optional
end-generation geometry. Type IIS processing is absent unless the endpoint
requests clone-ready ends.

A local realization is one exact local precursor, enzyme binding, operation
program, and state trajectory within its declared neighborhood. A basal local
realization ends at the nicked boundary plus proximal adapter-pairing and
upstream completion obligations; it does not assert a finalized adapter,
hairpin-PCR duplex, or present cohesive end. A complete realization composes
exact local realizations around one payload, resolves complete materials, and
validates the staged route. Final-product and achieved-geometry groups are
reversible projections over realization identities; neither may erase
alternatives.

Construction sequence is classified as retained, transient, auxiliary, or
destination-associated. Compactness uses achieved endpoint geometry and
retained non-payload sequence only. It describes each realization; search
coverage is reported separately.

"Added stem" and "added DNA" also answer different questions. Added stem counts
paired positions beyond the supplied invariant stem at a named molecular stage.
The loop is unpaired DNA. Source fragments removed during processing and
auxiliary primer handles have their own roles. Construction cost reports the exact non-payload nucleotides
retained on each endpoint strand. It does not add the two local search ceilings
or equate a transient basal contact span with retained stem extension. Keep the
loop, added pairing, sticky-end-to-stem spacing and auxiliary materials separately visible.

Identical sticky-end words do not require identical added stem. The exposed
cloning sequences can stay the same while the paired DNA between an end and
the supplied stem, or between the supplied stem and loop, changes. Say which
region changes instead of calling all these bases "flanks." A loop length and
a paired foldback-arm length are separate requirements. Short-loop limits belong
to the caller's request. Another application can permit longer loops without
changing HOP's general model.

## Conditional molecular choices

A **neighborhood** names the region being explored: loop, loop-side closing stem,
open/assembly side, supplied stem or stage-specific released interfaces.
A **variant** is an observed sequence/contact/terminal choice in that neighborhood,
supported by at least one complete preparation. It is not an independently
composable part. A **preserved property** names both its molecular stage and fixed
comparison reference. A **complete product** has a stage-qualified molecular
identity; a **preparation** supplies the verified route and materials producing it.

A conditional query narrows whole products through these choices. One variant
may leave several products; one product may have several preparations. Product
previews, fixed references and explicit selections remain distinct. Replacement
of one neighborhood keeps every other pin and preserved requirement active.
See [conditional exploration](../guides/explore-conditional-variants.md).

## Design inputs and hairpin structure

`Payload` is the input sequence to be paired. `ExactPayload` uses only
`A/C/G/T`; `DegeneratePayload` retains DNA IUPAC symbols. Its paired payload arm
is always derived by reverse complement.

`FoldbackJunction` is the contiguous physical junction between the authored
payload arm and its returning paired arm. It contains a retained stem-forming
tract, an explicitly bounded source-turn span, any declared turn extension, a
`foldback_arm`, and one ordered physical
pair observation for every aligned position. A cap-only junction has a
zero-length retained tract, a zero-length foldback arm, and no invented pair
observations; its nonempty turn remains explicit.

`BasalJunction` is the paired junction at the open end of the payload duplex.
It has declared left and right arms, a base-pair count, and ordered physical
pair observations. Nicked and surviving strand roles belong to processing
events and views, not to the junction itself.

In a source–Y-adapter construction, distinguish that basal association from the
whole upstream source flank. The flank can provide source-PCR primer homology
and later a source-side hairpin-PCR handle. The association records the actual
source–adapter contacts, including permitted noncanonical pairs. Beyond those
contacts, the two handles are unpaired with each other and each binds its own
hairpin-PCR primer. A nucleotide can serve different roles in different states.
Later released-insert sticky ends have their own words, polarities and
end-to-stem distances. Equal-length arms in an aligned paired-core representation
do not require equal handle lengths or equal released-end distances.

`PairedStemExtension` is optional non-payload paired context between the basal
junction and payload stem. Its literal equal-length arms can contain
Watson-Crick pairs, G:T wobbles, or hard mismatches. It is not part of the
payload and does not enlarge the S3/S2/S1/S0 basal profile.

`JunctionPairObservation` records literal left/right bases, antiparallel
indexes, and a `watson_crick`, `gt_wobble`, or `hard_mismatch` call. Exact
defaults and evaluated noncanonical junctions use this same representation.

`DesignDerivation` is a deterministic account of how HOP resolved or evaluated
the components in a `HairpinEncodingInsert`. It may record catalog junction
resolution, component evaluation, or caller-asserted nick and release projection
geometry. Those projections support encoding derivation; they are not an ordered
laboratory history. Construction programs and named `MethodPlan` objects own their respective
temporal molecular-state histories.

`EvaluatedComponentDerivation` composes caller-supplied foldback and basal
components with the authored payload without asserting an enzyme route. It
records physical evaluation and composition, not how a component was discovered or inherited.
Historical lineage and application interpretation stay in the caller and can
be linked through neutral external references.

## Compiled design and modeled molecular products

`HairpinEncodingInsert` is the compiler-owned one-dimensional sequence that
encodes a hairpin core. It contains a digest of its normalized literal or
symbolic sequence and nested
features that partition the sequence. It does not describe strandedness,
topology, a PCR product, or destination-specific assembly ends.

`HairpinPcrDuplex` records the duplex derived by the hairpin-PCR step: two
explicit complementary strands, exact primer boundaries, terminal chemistry,
and coordinate lineage. A later restriction event changes only its assembly ends.

`RestrictionDigestProduct` is a destination-neutral duplex fragment derived
from two facing restriction sites. It records both strand sequences, both exact
cohesive ends, the primary-strand union, and an oriented
`HairpinEncodingInsert` sequence projection. The caller checks its ends and
orientation against a destination before assembly.

`AssemblyFragment` is a destination-specific physical input with the ends and
orientation required by an assembly plan. It belongs to the caller and its
generic composition service, not to HOP.

## Physical evaluation and caller policy

`BasalConstraintProfile` is explicit caller policy applied after physical pair
classification. Its active, reserve, and reject decisions are not molecular
pair kinds. Its support and disruption thresholds use the dimensionless
`pair-count-weighted@1` heuristic: Watson-Crick, wobble, and hard-mismatch
pairs contribute `1`, `0.5`, and `0` to `pair_support_index`, and the reverse
weights to `pair_disruption_index`. The caller supplies application thresholds
for these weighted pair counts.

## Catalogs and bounded discovery

`ProcessingCatalog` is a strict caller-supplied set of nicking and release
agents. HOP can resolve concrete site geometry or classify symbolic motif
presence as `guaranteed`, `possible`, or `absent`; it ships no private or
application-specific processing catalog.

`NickingPlacementTarget` describes a desired nick boundary and strand plus the
paired tract and available turn that may contain a recognition site.
`search_nicking_placements` compares that target with caller-supplied nicking
agents and reports exact or nearest sequence and cut coordinates. Select a
placement explicitly before resolving an exact precursor.

`FoldbackPrecursorSearchRequest` materializes one selected nicking placement
inside caller-authored IUPAC sequence domains. `precursor_template` and
`turn_extension_template` state exactly which bases HOP may choose; HOP does
not invent unconstrained filler outside those domains. A
`FoldbackPrecursorCandidate` contains the exact precursor, derived
reverse-complement foldback arm, intended nick site, extra-site measurements,
and complete foldback evaluation. Its measurements remain inspectable, while
bounded output uses literal precursor and turn-extension content order rather
than a hidden quality objective. Catalog tier, vendor, procurement, and
application preference remain caller policy.

`BasalCandidateSearchRequest` declares two four-nucleotide IUPAC arm domains,
one caller-owned constraint profile, and whether
reserve results are selectable. `BasalCandidate` is an exact arm pair plus its
complete `BasalEvaluation`; it does not imply that an enzyme route can produce
the pair. `BasalCandidateExclusionSummary` accounts for evaluated reserve or
reject outcomes not returned by that request. The result's `canonical_ordinal`
follows literal arm content so consumers can reproduce the same bounded result.

`BasalProcessingGeometryRequest` asks whether a selected release geometry and
one caller-supplied nicking catalog can support an exact terminal nick around a
four-base retained scar. Its coordinates are signed relative to the release
top cut. `retained_scar_template` describes allowed scar bases;
`post_nick_template` describes the caller's allowed domain after the terminal
nick. `post_nick_domain_mode` states whether a process footprint may narrow
that domain or must preserve it. A compatible geometry is not yet a selected
route and does not imply that a particular left/right basal pair was chosen.

`BasalProcessingRouteCandidate` joins one exact `BasalCandidate` to one exact
processing geometry. Its retained scar is the basal left arm. Compatibility
requires every scar base to satisfy the geometry domains and requires the scar
not to contain the selected release motif in either orientation. The candidate
derives its terminal nick and surviving strand from the processing geometry.
It is a basal processing route, not a released-foldback route and not a caller
preference.

`ReleasedFoldbackGeometryRequest` asks whether a caller-supplied nicking agent,
release agent, release orientation, and exact or nearby nick boundary can share
one precursor while supporting the declared exposed strand, paired tract, and
turn. `ReleasedFoldbackGeometryHit` records both process footprints, literal
cuts, the active-product extent, correlated Watson-Crick pairing domains, and
the exact number of compatible precursor sequences. It is a geometry result,
not a selected sequence, released state, basal route, or caller preference.

`ReleasedFoldbackPrecursorSearchRequest` selects one released-foldback geometry
and supplies one complete caller-authored IUPAC precursor template. The search
intersects that template with the geometry's base and correlated pair domains.
A `ReleasedFoldbackPrecursorCandidate` is one exact sequence with its digest,
selected geometry identity, content identity, and `canonical_ordinal`. It is not a
released molecular state, a basal route, or a complete production method.

`HairpinJunctionRouteCandidate` joins one exact released-foldback precursor to
one exact basal-processing route. It contains the projected
`ReleasedStrandState` and is compatible only when that state's active strand is
the strand that survives basal terminal nicking. The two end processes may use
different release agents; their identities and orientations remain explicit.
This route covers the junction processes. Complete source construction and
destination checks are separate operations. Its exact precursor is checked
against the embedded geometry even after the route is extracted from its search
result. A routed workflow view derives from this
object and cannot substitute an independent foldback evaluation.

## Molecular states, materials, and views

`ReleasedStrandState` records the active product, retained partner, literal
strand roles, cut and nick boundaries, precursor span, and per-base coordinate
lineage after one explicit release event. Molecular sequences are stored 5′→3′;
bottom-strand lineage therefore traverses top-precursor indexes in reverse.

`WorkflowView` is the renderer-independent scientific view contract. It owns
panels, tracks, features, pair calls, and strand direction. SVG is one
deterministic rendering and cannot change the molecular state.

`ProcessOligo` is a vendor-neutral sequence material with explicit terminal
modifications. `OligoBinding` records how a primer binds a declared source or
adapter terminus. Materials are inputs to method events; they are not molecular
intermediate states.

`MolecularStrand`, `Fragment`, `StrandPairObservation`, and `CovalentBond` are
method-neutral primitives. They preserve literal sequences, 5′→3′ orientation,
terminal chemistry, per-base lineage, physical pair calls, and ligation joins.
The public API does not accept an arbitrary caller-authored event graph.

## Named methods

`linear-source-multinick-size-selection-hairpin-pcr@1` names the implemented
method that resolves a source-PCR duplex, every nick site, denatured fragments,
length selection, adapter annealing, ligation, hairpin PCR, and a facing
restriction product.

`circular-precursor-exonuclease-selection-multidigest-hairpin-pcr@1` names a
distinct method family whose implementation is unavailable. Its name records
transformations. HOP returns `unavailable` and `not_evaluated` until that method
has a request contract and compiler.

`MethodOutcome` keeps `implementation_status` separate from
`resolution_status`. Availability is `available` or `unavailable`; resolution
is `not_evaluated`, `complete`, `infeasible`, or `truncated`. These fields do
not replace sequence identity or destination readiness.

## Provenance and verification

`MethodBundle` is the portable derivation record for one complete method request. It
contains the strict request and plan plus exports derived from that plan. It is
separate from `HopBundle`: the former records production-method resolution,
while the latter records hairpin-design compilation. They may share a
hairpin-encoding sequence digest without sharing identity or ownership. A
consumer must not infer that relationship from two otherwise valid bundles;
the method request or handoff must establish exact digest equality.

## Diagnostics

`Diagnostic` is a stable, machine-readable explanation of expected design
infeasibility. Invalid schemas or corrupt software configuration are exceptions,
not diagnostics.
