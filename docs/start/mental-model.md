---
doc_id: hop-mental-model
title: From payload to hairpin construction
intent: Explain the fixed payload, searchable junctions, required materials, and limits of a computed construction.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-11-09
doc_type: explanation
journey:
  - compile
  - discover
  - method
  - verify
  - integrate
---

# From payload to hairpin construction

Start with the duplex sequence you want the hairpin to present. That payload
stays fixed while HOP searches the surrounding sequence and enzyme arrangements.
You can inspect where a junction is possible, what bases and cuts it requires,
and whether selected junctions can be completed into the requested product.

## What do you specify?

Author one payload arm as exact DNA or fixed and degenerate positions. HOP
derives its complementary arm; you do not specify the two independently.
Compiling this anatomy gives the intended hairpin sequence, not a construction
procedure. See [substrate spaces](../guides/substrate-spaces.md).

For construction, start with the stem and intended product using
[design discovery](../guides/discover-designs.md). End words, scaffold properties
and methods are optional constraints. A versioned context declares the available
enzymes, geometry and material permissions; inspect or replace it as needed. The physical starting material
is a source ssDNA oligo with construction flanks around the payload. Its sequence
and required auxiliaries depend on the chosen route.

The foldback neighborhood supplies the sequence that can be exposed, folded,
and joined to close the cap. The basal construction neighborhood supplies the
opposite junction, including adapter pairing and later end generation when required.
Neither search changes the payload.

## How do local junctions become a construction?

A local solution describes a possible junction, not the entire molecule.
Composition checks selected junctions together with the source, adapters,
primers, fragment-removal program, and endpoint requirements. Missing annealing
sequence or incompatible materials must reject that proposed construction.

For the supported linear-source route, the modeled sequence of steps is:

```text
source ssDNA + primers → source duplex
    → cleavage → strand separation → fragment selection
    → foldback and required adapter pairing → covalent joins → ssDNA hairpin
    → optional PCR duplex → optional end-generating cleavage
```

Nicking breaks one backbone; it does not itself remove a fragment. Separation
and selection are distinct steps. PCR derives expected strands from declared
primer bindings; HOP does not predict amplification efficiency.

The requested endpoint determines which steps and materials are required.
A direct ssDNA hairpin does not acquire adapter, PCR, or end-generation
requirements merely because another endpoint needs them. For material and
request examples, use the [construction guide](../guides/compile-construction.md)
or [check a named method](../guides/resolve-production-method.md).

## What can the search change?

HOP solves and reuses foldback and basal sequence domains separately, then checks selected combinations through the
complete preparation. Most coupling is within each neighborhood: its geometry,
recognition sites, cleavage and sequence must agree. Composition adds the
requirements shared by the full molecule and its processing route. Modularity
therefore enables reuse; it does not make every pair of local solutions a
verified construction.

For adapter-bearing routes, **basal association** means the source–adapter contact
region; it is narrower than the whole upstream construction flank. The source-side
and adapter-side unpaired handles extend beyond that
association and provide homology for hairpin PCR. A source-side sequence can also
serve an earlier source-PCR primer; these are stage-specific uses of the same
bases. Permitted mismatches belong to the association record, not the unpaired
handles.

The scaffold-completion search seeks a working auxiliary completion for each
consequential scaffold assignment; it does not enumerate every interchangeable
PCR handle. Bases that contribute to association or a retained product stay
explicit. Primer requirements and unwanted recognition sites still constrain
the remaining auxiliary bases. If one completion fails, other permitted
completions remain available.

Choose which parts of the request to preserve or explore:

| Intention | What HOP preserves or explores |
| --- | --- |
| Preserve my experimental stem | The supplied sequence and its derived complementary arm |
| Find different constructions | Permitted loop, paired extensions, basal contacts, ends, gaps and methods |
| Reuse my materials | Explicitly fixed source, adapter or primer sequences and chemistry |
| Start from a useful source handle | A soft `source_handle_seed` in the construction context; scaffold constraints and complete-route checks still determine the completed materials |

Reusing an oligo can restrict which constructions work. Preserving the stem alone
does not require reusing its original primers. An adapter's paired segment belongs
to the coupled basal problem; its unpaired handle has a different role. A primer
can span both roles, so HOP derives their boundaries from the route rather than
treating every base of a primer as interchangeable auxiliary sequence.

The default released-insert context permits bounded source-context variation and
uses scaffold completion. Other contexts may fix more material. Read the resolved
permissions before extending an example: copying an exact handle also copies its
recognition sites and length restrictions. A failed fixed completion does not
exclude the scaffold under broader material permissions.

The **released-insert interfaces** are later products of duplex digestion. Their
sticky words, polarities and paired distances to the supplied-stem boundaries are
separate from basal association length. Equal source–adapter contact spans do not
require equal unpaired handles or equal left/right insert distances. The exact cut positions determine
which construction bases survive.

Foldback-local discovery treats the PCR-amplified material as a duplex. Unless
the caller constrains the physical nick strand, HOP searches both exact nick
strands by default and retains only routes permitted by the enzyme's declared
recognition orientation and cut contract.

For a basal search, the cohesive end can be fixed or specified as an IUPAC
pattern. Pairing constraints determine where an adapter may differ from the
displaced source strand. Recognition sites must be valid in the molecular state
where the relevant enzyme acts; a later adapter cannot supply a site required
in the initial source duplex.

Searches explore increasing retained non-payload sequence. An existence search
keeps a witness for each accessible work unit; an all-realizations search keeps
every exact alternative within its reported coverage. Neither order nor a
shorter junction predicts experimental performance. A truncated search leaves
part of the declared space unresolved. See [search interpretation](../discovery/overview.md).

## How does a preparation enter the atlas?

Discovery asks whether an assignment can satisfy the requested construction.
For a complete preparation, **satisfiable** means there is an exact choice of
sequences, materials and ordered operations that passes the modeled constraints
through the requested endpoint. A valid local basal or foldback arrangement is
only one part of that proof. It must still compose with the other neighborhood,
primer bindings, sites, cuts and joins. This is sequence/geometry validity, not
a prediction of experimental performance.

Keep these decisions separate:

| Decision | What it changes |
| --- | --- |
| Molecular permissions | Which stems, ends, lengths, sequences, contacts, methods and materials are allowed; a violation rejects that assignment |
| Compactness | Length ceilings restrict the domain; traversal favors compact alternatives without proving a global minimum |
| Diversity objective | Which permitted alternatives receive search effort earlier; it does not waive constraints or award admission points |
| Computing limits | How much of the domain is explored now; unfinished work remains unresolved |
| Atlas capture and query | Which recorded complete preparations are included or visible; an explicit query or identity list may select a subset |

There is no hidden preparation-quality score. The current construction
preference contract has `ranking: none`. A longer construction inside the
declared bounds remains eligible; being longer is not itself a rejection or an
experimental penalty. Search order can affect which preparations are found in a
bounded run, even when there is no ranking of the resulting preparations.

"Added stem" and "added DNA" also answer different questions. Added stem counts
paired positions beyond the supplied invariant stem at a named molecular stage.
The loop is unpaired DNA; source fragments removed during processing and
auxiliary primer handles have their own roles. Construction cost reports the exact non-payload nucleotides
retained on each endpoint strand. It does not add the two local search ceilings
or equate a transient basal contact span with retained stem extension. Keep the
loop, added pairing, sticky-end-to-stem spacing and auxiliary materials separately visible.

The API fields `left_gap` and `right_gap` measure this spacing on the released
insert: the paired positions between each sticky end and its supplied-stem
boundary. Zero puts that sticky end directly beside the stem; two retains two
additional paired positions there. A gap is not missing DNA, a primer handle or
a loop extension. Sticky-end words and these distances are separate inputs.

Identical sticky-end words do not require identical added stem. The exposed
cloning sequences can stay the same while the paired DNA between an end and
the supplied stem, or between the supplied stem and loop, changes. Say which
region changes instead of calling all these bases "flanks." A loop length and
a paired foldback-arm length are separate requirements. Short-loop limits belong
to the caller's request; another application can permit longer loops without
changing HOP's general model. Neither choice asserts reaction efficiency.

By default, freezing an atlas includes all matching recorded preparations,
deduplicated by preparation identity. It does not choose only shortest designs
or best-scoring molecules. A captured subset must retain its explicit selection
scope. UMAP then arranges molecular descriptors for navigation; its distances,
clusters and point density neither admit preparations nor measure how uniformly
the permitted space was searched. Different preparation methods can produce the
same product, and many valid preparations may remain undiscovered.

Use [survey scope and search](../reference/interface-survey-search.md) for
request bounds, traversal and completion semantics, and
[atlas capture](../guides/share-atlas-edition.md) for saved membership. The API,
CLI and browser use these same request, choice and selection authorities.

## What can you conclude?

Separate local variation from complete combinations. Two preparations may differ
in the foldback, the basal association, their released ends, or only the materials
used to make the same product. Count exact products at the intended molecular
stage, and inspect preparation alternatives separately. A geometry count cannot
capture all sequence differences; a preparation count cannot establish biological
library diversity.

Choose against your requirements first: available enzymes, permitted product
ends, pairing rules, and the materials you can supply or allow HOP to derive.
Then compare complete candidates using an explicit preference, such as less
retained construction sequence. An example's particular end sequence is not
a requirement for other designs. See the [construction guide](../guides/compile-construction.md)
for filtering, sorting, inspecting, and selecting alternatives.

A complete candidate can be found before a search is exhausted. Its completion
means that its declared molecular requirements are satisfied; it does not mean
that every alternative was examined or that this candidate is the shortest.
Keep the candidate's completeness separate from the search's coverage.

A successful computation supplies exact sequence and processing expectations.
[Verification](../provenance/overview.md) checks that the saved result follows
from its inputs. It does not establish recovery, folding, cleavage efficiency,
ligation efficiency, or biological activity. Defined cohesive ends also need
a separate compatibility check against the intended cloning destination.

Experimental protocols, tubes, controls, and observations belong in the
researcher's laboratory records, not in a computed molecular specification.
