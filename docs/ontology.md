---
doc_id: hop-ontology
title: HOP Design ontology
intent: Define the canonical public molecular and compiler vocabulary.
audience:
  - users
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
---

# HOP Design ontology

The hierarchy is:

```text
DesignSpec  -> HopPlan       -> HairpinEncodingInsert
MethodRequest -> method states -> RestrictionDigestProduct
HairpinEncodingInsert.digest == RestrictionDigestProduct.encoding_projection.digest
RestrictionDigestProduct + caller destination -> AssemblyFragment
```

Discovery proposes compatible geometry. Caller policy selects among candidates.
Views and files project derived state; they do not become a second authority.

## Design inputs and hairpin structure

`Payload` is the input sequence to be paired. `ExactPayload` uses only
`A/C/G/T`; `DegeneratePayload` retains DNA IUPAC symbols. Its paired payload arm
is always derived by reverse complement.

`FoldbackJunction` is the contiguous physical junction between the authored
payload arm and its returning paired arm. It contains a retained stem-forming
tract, the short unpaired `turn`, a `foldback_arm`, and one ordered physical
pair observation for every aligned position. A cap-only junction has a
zero-length retained tract, a zero-length foldback arm, and no invented pair
observations; its nonempty turn remains explicit.

`BasalJunction` is the paired junction at the open end of the payload duplex.
It has declared left and right arms, a base-pair count, and ordered physical
pair observations. Nicked and surviving strand roles belong to processing
events and views, not to the junction itself.

`PairedStemExtension` is optional non-payload paired context between the basal
junction and payload stem. Its literal equal-length arms can contain
Watson-Crick pairs, G:T wobbles, or hard mismatches. It is not part of the
payload and does not enlarge the S3/S2/S1/S0 basal profile.

`JunctionPairObservation` records literal left/right bases, antiparallel
indexes, and a `watson_crick`, `gt_wobble`, or `hard_mismatch` call. Exact
defaults and evaluated noncanonical junctions use this same representation.

`ProcessingRoute` is a reusable physical implementation that produces a
resolved foldback and basal junction. `resolved_events` records explicit
caller-supplied release nick, optional release, foldback, basal-pairing,
terminal-nick, and insert-assembly transitions. The generic direct-synthesis
route is a synthetic software demonstration, not a lab protocol.

`component_assembly` composes caller-supplied foldback and basal components with
the authored payload without asserting an enzyme route. It records physical
evaluation and composition, not how a component was discovered or inherited.
Historical lineage and application interpretation stay in the caller and can
be linked through neutral external references.

## Compiled design and physical products

`HairpinEncodingInsert` is the compiler-owned one-dimensional sequence that
encodes a hairpin core. It contains an exact sequence digest and nested
features that partition the sequence. It does not describe strandedness,
topology, a PCR product, or destination-specific assembly ends.

`HairpinPcrDuplex` is the physical duplex produced by hairpin PCR. It contains
two explicit complementary strands, exact primer boundaries, terminal
chemistry, and coordinate lineage. PCR creates the duplex; a later restriction
event only changes its assembly ends.

`RestrictionDigestProduct` is a destination-neutral duplex fragment derived
from two facing restriction sites. It records both strand sequences, cohesive
cut boundaries, the primary-strand union, and an oriented
`HairpinEncodingInsert` sequence projection. It is not automatically ready for
assembly.

`AssemblyFragment` is a destination-specific physical input with the ends and
orientation required by an assembly plan. It belongs to the caller and its
generic composition service, not to HOP.

## Physical evaluation and caller policy

`BasalConstraintProfile` is explicit caller policy applied after physical pair
classification. Its active, reserve, and reject decisions are not molecular
pair kinds. Application thresholds remain with their owners.

## Catalogs and bounded discovery

`ProcessingCatalog` is a strict caller-supplied set of nicking and release
agents. HOP can resolve concrete site geometry or classify symbolic motif
presence as `guaranteed`, `possible`, or `absent`; it ships no private or
application-specific processing catalog.

`NickingPlacementTarget` describes a desired nick boundary and strand plus the
paired tract and available turn that may contain a recognition site.
`search_nicking_placements` compares that target with caller-supplied nicking
agents and reports exact or nearest geometry. A placement is a physical search
result for sequence and cut coordinates, not evidence of empirical cleavage,
an application selection, or an orderable oligo.

`FoldbackPrecursorSearchRequest` materializes one selected nicking placement
inside caller-authored IUPAC sequence domains. `precursor_template` and
`turn_extension_template` state exactly which bases HOP may choose; HOP does
not invent unconstrained filler outside those domains. A
`FoldbackPrecursorCandidate` contains the exact precursor, derived
reverse-complement foldback arm, intended nick site, extra-site measurements,
and complete foldback evaluation. Candidate order uses molecular measurements
only. Catalog tier, vendor, procurement, and application preference remain
caller policy.

`BasalCandidateSearchRequest` declares two four-nucleotide IUPAC arm domains,
one G:T interpretation, one caller-owned constraint profile, and whether
reserve results are selectable. `BasalCandidate` is an exact arm pair plus its
complete `BasalEvaluation`; it does not imply that an enzyme route can produce
the pair. `BasalCandidateExclusionSummary` accounts for evaluated reserve or
reject outcomes not returned by that request. The result's canonical physical
order is an interoperability order, not an experimental preference.

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
selected geometry identity, content identity, and canonical rank. It is not a
released molecular state, a basal route, or a complete production method.

`HairpinJunctionRouteCandidate` joins one exact released-foldback precursor to
one exact basal-processing route. It contains the projected
`ReleasedStrandState` and is compatible only when that state's active strand is
the strand that survives basal terminal nicking. The two end processes may use
different release agents; their identities and orientations remain explicit
rather than being collapsed into a same-agent rule. This is a junction-level
route, not a complete source molecule, wet-lab method, or assembly claim. Its
exact precursor is checked against the embedded geometry even after the route
is extracted from its search result. A routed workflow view derives from this
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

## Named methods and portable evidence

`linear-source-multinick-size-selection-hairpin-pcr@1` names the implemented
method that resolves a source-PCR duplex, every nick site, denatured fragments,
length selection, adapter annealing, ligation, hairpin PCR, and a facing
restriction product.

`circular-precursor-exonuclease-selection-multidigest-hairpin-pcr@1` names a
distinct method family whose implementation is unavailable. Its name records
transformations rather than roadmap status; HOP makes no feasibility claim for
that method until a request contract and compiler exist.

`MethodOutcome` keeps `implementation_status` separate from
`resolution_status`. Availability is `available` or `unavailable`; resolution
is `not_evaluated`, `complete`, `infeasible`, or `truncated`. These fields do
not replace sequence identity or destination readiness.

`MethodBundle` is the portable evidence for one complete method request. It
contains the strict request and plan plus exports derived from that plan. It is
separate from `HopBundle`: the former records production-method resolution,
while the latter records hairpin-design compilation. They may share a
hairpin-encoding sequence digest without sharing identity or ownership.

## Diagnostics

`Diagnostic` is a stable, machine-readable explanation of expected design
infeasibility. Invalid schemas or corrupt software configuration are exceptions,
not diagnostics.
