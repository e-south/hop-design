# Molecular meaning and construction search

Use these terms to distinguish a molecule's physical features, the route that
makes it and the scope of a search result.

Return to the [ontology reference](../ontology.md).

## Describe the molecule before its construction role

Start with the supplied stem. The foldback neighborhood closes one end; the
basal neighborhood supports adapter association at the other. These are roles
in the preparation, while stem, loop, tail and overhang describe physical
features in a named molecular state.

| Feature | Where to locate it | Construction interpretation |
| --- | --- | --- |
| Paired stem | Opposing positions on the folded strand | The supplied experimental sequence and its derived complement; added pairing is measured separately |
| Loop | Unpaired bases joining the two stem arms | The closing sequence; its size follows its exact sequence |
| Tail | Unpaired sequence at a strand terminus | May supply primer homology, be removed, or contribute to a later product; ancestry determines which |
| Noncanonical contact | Two recorded interacting positions | An explicitly permitted mismatch or wobble; it is not an unpaired tail |
| Overhang | Protruding sequence on the released duplex | An assembly interface, with its sequence read 5′→3′ on that strand |

A nucleotide may have several construction roles across processing states.
Primer homology upstream of the basal region is not synonymous with basal
pairing. An annealing minimum is a requirement; the achieved paired span is a
measurement. A nick breaks one backbone at a boundary; a recognition footprint
occupies an interval.
The [parameter registry](../../reference/molecular-parameters.md) supplies units,
measurement boundaries and dependencies, including `R = A − D` and loop length
from the loop word. Equivalent measurements are counted once.

This separation of structural feature from contextual annotation follows the
useful representational principle illustrated by
[bpRNA](https://doi.org/10.1093/nar/gky285). HOP derives its contacts from the
construction's molecular states.

The atlas descriptor `x` records these measurements, retained regional sequences,
contacts and assembly interfaces. Contact codes identify base pairs and contact
classes; subtracting the codes has no molecular meaning. A recorded comparison
policy scales and weights groups of measurements to calculate molecular
dissimilarity. The UMAP plot uses those distances to place similar products near each other.
The invariant stem, duplicated measurements and preparation identifiers do not
add distance dimensions. Methods remain available for inspection and further
search. Each selectable point has a complete preparation with a verified route
and exact materials; its plot position comes from the comparison policy.

## Construction search and its molecular meaning

One request defines the permitted sequences, geometry, methods and materials.
Together these choices form its **molecular domain**. Search first finds choices
that satisfy necessary constraints, then asks the complete compiler to check
their preparations. Conditional plots, sequence views at named processing stages
and oligo exports present those verified records; they do not recalculate the
molecule independently.

| Term | Biological or computational meaning |
| --- | --- |
| Permitted domain | Authored stem, joint interface choices, geometry, methods and material permissions; a computing quota does not narrow it |
| Necessary relation | Combinations that satisfy the constraints HOP can translate into the relation, including dependencies between base choices; membership alone does not establish a complete route |
| Local neighborhood | Foldback or basal construction region with its own sequence, geometry and processing constraints; local solutions are reusable inputs to complete construction checks |
| Candidate assignment | A particular geometry, method and sequence choice to evaluate through the complete construction |
| Auxiliary completion | A choice of additional material bases under explicit permissions; some may affect retained sequence and cannot be treated as interchangeable |
| Product | The exact molecule at a named processing stage, with sequence, contacts and terminal chemistry |
| Preparation | A verified modeled route and exact materials producing the requested product; different preparations can produce the same product |
| Processing state | A recorded molecular state linked by copying, cleavage, association or joining; search traversal order is not a physical time course |
| Selection | A saved reference that identifies a verified preparation; a branch/page address alone does not identify the molecule |

For `paired_scaffold_completions`, paired or retained sequence that affects the
product remains explicit while other permitted handle bases are completed as
needed. This does not enumerate every exact unpaired hairpin or material variant.
When HOP cannot translate a requirement into the local sequence coordinates, it
evaluates the candidate through the ordinary checks rather than excluding it.

Material policies answer a separate question from the diversity objective:
`fixed` requires the exact material; `constrain` permits assignments within the
declared domain; `derive` constructs a material from the selected route and its
requirements. A `constrain` sequence containing only A/C/G/T still fixes every
base. IUPAC alternatives or a length range create a searchable domain. Auxiliary
completion must satisfy required homology, chemistry, recognition sites and
whole-route checks. It cannot repair a contradiction by changing a fixed material.

Foldback and basal domains are solved separately. A solution at each end does
not establish that they work together: the complete compiler must still resolve
the materials and check the combined route.
See [interface surveys](../../guides/survey-interfaces.md) and
[their contract](../../architecture/decisions/0052-resumable-interface-surveys.md).

## Design and method authorities

Design and method bundles independently record different derivations:

```text
DesignSpec -> DesignDerivation -> HairpinEncodingInsert -> HopBundle
                                      |
                                      | encoding-digest equality
                                      |
MethodRequest -> method states -> RestrictionDigestProduct -> MethodBundle

RestrictionDigestProduct + caller destination -> AssemblyFragment
```

Discovery proposes compatible geometry. Caller policy selects among candidates.
An encoding digest is a content fingerprint calculated from the normalized
encoding sequence.
Views and files present derived state; they do not supply an independent
definition of the molecule. Matching encoding digests establish that the two
bundles describe the same encoding sequence. Independently compiled bundles need
not match. Equality is checked when the method request supplies
`expected_hairpin_encoding`, or when the consumer performs the same exact
digest comparison before associating the products.

## Payload-centered construction vocabulary

A **basal association** is the recorded source–adapter contact region, with literal
paired positions and permitted contact classes. Unpaired source-side and
adapter-side handles lie beyond that association. Primer homology is a material
function at a declared stage; it may overlap another function in the same bases.

A **hairpin core** is the route-neutral design sequence and its supplied-stem,
foldback and basal features. For a released-insert construction, HOP locates the
core within the PCR parent. The **released insert** is the exact pair of strands
retained by end-generating cuts. Its **union** spans the parent positions retained
on either strand. That union need not equal the core: cuts may remove outer
construction bases while retaining other construction bases. The protected
interval containing both supplied-stem copies and foldback remains intact on
both strands. End words and paired end-to-stem distances describe this released
state; they do not describe the hairpin handles.

Construction starts from the user-defined duplex payload, with positions measured
in the final product. Its reference strand is authored 5-prime to
3-prime, its aligned complement is derived, and its basal and foldback
boundaries are explicit. A route family owns the mapping from these positions
to one or more source-material segments. The current family,
`linear_source/v1`, uses a contiguous source encoding. Other route families need
not share that property.

### Local results and complete preparations

An endpoint names the requested molecular product. `ssdna_hairpin` ends at the
closed single-stranded hairpin. `adapter_ligated_hairpin` includes adapter
capture and joining; `hairpin_pcr_duplex` continues through hairpin PCR.
`clone_ready_duplex` adds declared end-generating cleavage and exact cohesive
ends. Endpoint choice determines required neighborhoods, materials, operations
and states.

A **local realization** specifies an exact precursor, enzyme binding, operations
and resulting states within one declared neighborhood. A basal local realization
reaches the nicked boundary and records proximal adapter pairing and upstream
completion requirements. It does not yet specify a finalized adapter,
hairpin-PCR duplex or present cohesive end.

A **complete realization** combines exact local realizations around one payload,
resolves the complete materials and validates the staged route. Its exact
endpoint molecule is the **product**; the route and materials form the
**preparation**. Several preparations can therefore produce the same product.
Final-product and achieved-geometry groups reference every exact realization
they contain, preserving alternatives within each group.

A local-neighborhood request defines a foldback or basal construction question.
It combines final payload, route family, endpoint,
family-specific target geometry, required constraints, design preferences,
caller-provisioned enzymes, explicit relaxation, and finite enumeration. Its
result preserves requested and achieved geometry, the permitted relaxation used,
every exact local solution, rejection counts and reasons, and search completion
evidence. Its grouped views retain the identities of all underlying solutions.

A foldback target is described by `junction_offset_nt`, `loop_length_nt`, and
`annealing_arm_length_bp`. A basal target describes endpoint-dependent nick
geometry, an exact ligation-proximal-outward pairing state, and optional
end-generation geometry. Type IIS processing is absent unless the endpoint
requests clone-ready ends.

### Added stem and retained DNA

Construction sequence is classified as retained, transient, auxiliary, or
destination-associated. Compactness uses achieved endpoint geometry and
retained non-payload sequence only.

"Added stem" and "added DNA" also answer different questions. Added stem counts
paired positions beyond the supplied invariant stem at a named molecular stage.
The loop is unpaired DNA. Source fragments removed during processing and
auxiliary primer handles have their own roles. Construction cost reports the
exact non-payload nucleotides retained on each endpoint strand. It does not add
the two local search ceilings or equate a transient basal contact span with
retained stem extension. Keep the loop, added pairing, sticky-end-to-stem spacing
and auxiliary materials separately visible.

On the released insert, **end-to-stem spacing** counts paired positions between
each sticky end and its supplied-stem boundary. The API fields `left_gap` and
`right_gap` describe these distances. Zero places the end directly beside the
stem. These paired-base counts are separate from loop length and unpaired handles.

Identical sticky-end words do not require identical added stem. The exposed
cloning sequences can stay the same while the paired DNA between an end and
the supplied stem, or between the supplied stem and loop, changes. Say which
region changes instead of calling all these bases "flanks." A loop length and
a paired foldback-arm length are separate requirements. Short-loop limits belong
to the caller's request. Another application can permit longer loops without
changing HOP's general model.

## Search coverage and ranking

Search coverage records which part of the declared domain HOP examined.
Feasibility records whether that work found a valid realization, ruled out the
domain or left the question unresolved. Finding one complete preparation can
establish feasibility before the search is exhausted. A truncated search cannot
establish infeasibility; unexamined alternatives remain unresolved.

Large exact sequence domains may be divided into deterministic, disjoint
execution parts without changing the molecular problem or realization
identities. One part does not establish whole-domain payload compatibility.

Compactness describes a realization, while length ceilings bound the domain.
Traversal can favor compact alternatives without proving a global minimum.
The construction preference contract has `ranking: none`: a longer realization
within the declared bounds remains eligible. Search order can affect which
results a bounded run finds. See
[search interpretation](../../discovery/overview.md) for stopping and coverage
semantics.

## Conditional molecular choices

A **neighborhood** names the region being explored: loop, loop-side closing stem,
open/assembly side, supplied stem or stage-specific released interfaces.
A **variant** is an observed sequence/contact/terminal choice in that neighborhood,
supported by at least one complete preparation. It is not an independently
composable part. A **preserved property** names both its molecular stage and fixed
comparison reference. A **complete product** is identified by its exact molecular
state at a named processing stage; a **preparation** supplies the verified route
and materials producing it.

A conditional query narrows whole products through these choices. One variant
may leave several products; one product may have several preparations. Product
previews, fixed references and explicit selections remain distinct. Changing one
neighborhood keeps every other fixed choice and preserved requirement active.
See [conditional exploration](../../guides/explore-conditional-variants.md).
