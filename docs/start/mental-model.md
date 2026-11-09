# From payload to hairpin construction

Start with the duplex region you want the hairpin to present: the **payload**, or
supplied stem. A hairpin is one continuous DNA strand folded into paired arms
joined by an unpaired loop. You supply one payload arm; HOP derives its complement.
The payload stays fixed while HOP searches the surrounding sequence and enzyme
arrangements. You can inspect possible junctions, the bases and cuts they
require, and whether they can be combined into the requested product.

## What do you specify?

Author one payload arm as exact DNA or a sequence containing fixed and degenerate
positions. HOP derives its complementary arm. Compiling this anatomy gives the
intended hairpin sequence; discovery finds construction procedures. See
[substrate spaces](../guides/substrate-spaces.md) for sequence compilation.

The **product** is the exact molecule at a named processing stage. A **route**
is the ordered series of steps that makes it. A **preparation** specifies the
route and its exact source, adapters, primers and terminal chemistry. Different
preparations can make the same product.

For construction, start with the stem and intended product using
[design discovery](../guides/discover-designs.md). End words, scaffold properties
and methods are optional constraints. A versioned context declares the available
enzymes, geometry and material permissions. The physical starting material is a
source ssDNA oligo with construction flanks around the payload. Its sequence and
required auxiliary materials depend on the chosen route.

HOP calls the two construction regions **local neighborhoods**. The foldback
neighborhood supplies the sequence that can be exposed, folded and joined to
close the loop end. The basal neighborhood supplies the opposite, open-end
junction, including adapter pairing and later end generation when required.
Neither search changes the payload.

## How do local junctions become a construction?

A **local realization** records an exact junction sequence and its processing
within one neighborhood. It is an input to composition, which combines selected
junctions and checks the source, adapters, primers, fragment removal and endpoint
requirements together. Two valid local realizations can still fail composition
if their materials are incompatible or required annealing sequence is missing.

For the supported linear-source route, the modeled sequence of steps is:

```text
source ssDNA + primers → source duplex
    → cleavage → strand separation → fragment selection
    → foldback and required adapter pairing → covalent joins → ssDNA hairpin
    → optional PCR duplex → optional end-generating cleavage
```

Nicking breaks one backbone. Strand separation exposes the fragments; selection
retains the required ones. PCR derives expected strands from declared primer
bindings.

The requested endpoint determines which steps and materials are required.
The direct ssDNA endpoint requires the hairpin; later endpoints add adapter
ligation, hairpin PCR or end-generating cleavage. For material and
request examples, use the [construction guide](../guides/compile-construction.md)
or [check a named method](../guides/resolve-production-method.md).

## What can the search change?

HOP searches the permitted foldback and basal sequences separately and can reuse
those local results. Within each neighborhood, lengths and relative positions
(the **geometry**) must agree with recognition sites, cleavage and sequence. It
then checks selected combinations against the complete preparation's shared
requirements.

For adapter-bearing routes, **basal association** means the source–adapter contact
region. The unpaired source-side and adapter-side handles extend beyond it and
provide homology for hairpin PCR. A source-side sequence can also bind an earlier
source-PCR primer: the same bases can serve different roles at different steps.
Permitted mismatches describe contacts within the association.

The **scaffold** is the construction sequence and pairing around the supplied
stem, including its loop and added paired regions. Scaffold completion fills in
the other permitted material bases needed to make it, such as PCR handles. It
seeks a working completion for each scaffold assignment. Bases that contribute
to association or a retained product stay explicit; interchangeable handles are
not enumerated exhaustively. Primer requirements and unwanted recognition sites
still constrain auxiliary bases. If one completion fails, HOP can try other
permitted completions.

Choose which parts of the request to preserve or explore:

| Intention | What HOP preserves or explores |
| --- | --- |
| Preserve my experimental stem | The supplied sequence and its derived complementary arm |
| Find different constructions | Permitted loop, paired extensions, basal contacts, ends, gaps and methods |
| Reuse my materials | Explicitly fixed source, adapter or primer sequences and chemistry |
| Start from a useful source handle | A soft `source_handle_seed` in the construction context; scaffold constraints and complete-route checks still determine the completed materials |

Reusing an oligo can restrict which constructions work. Preserving the stem alone
does not require reusing its original primers. A primer can span both the adapter's
paired segment and its unpaired handle, so HOP derives those boundaries from the
route. It cannot treat every primer base as interchangeable auxiliary sequence.

The default released-insert context permits bounded source-context variation and
uses scaffold completion. Other contexts may fix more material. Read the resolved
permissions before extending an example: copying an exact handle also copies its
recognition sites and length restrictions. Failure with fixed materials does not
exclude the scaffold under broader material permissions.

The **released-insert interfaces** are produced by duplex digestion. Their sticky
words, polarities and paired distances to the supplied-stem boundaries are
separate from basal association length. Equal contact spans do not require equal
handle lengths or equal left/right insert distances. Exact cuts determine which
construction bases survive.

Foldback-local discovery treats the PCR-amplified material as a duplex. Unless
the caller constrains the physical nick strand, HOP searches both exact nick
strands by default and retains only routes permitted by the enzyme's declared
recognition orientation and cut contract.

For a basal search, the cohesive end can be fixed or specified as an IUPAC
pattern. Pairing constraints determine where an adapter may differ from the
displaced source strand. Recognition sites must be valid in the molecular state
where the relevant enzyme acts. A later adapter cannot supply a site required
in the initial source duplex.

Searches explore increasing retained non-payload sequence. An existence search
keeps an exact working example, called a **witness**, for each accessible work
unit. An all-realizations search keeps every exact alternative within its
reported coverage. A truncated search leaves part of the declared domain
unresolved. See [search interpretation](../discovery/overview.md).

## What makes a complete preparation valid?

A complete preparation is **satisfiable** when an exact choice of sequences,
materials and ordered operations passes the sequence and geometry constraints
through the requested endpoint.

Keep these decisions separate:

| Decision | What it changes |
| --- | --- |
| Molecular permissions | Which stems, ends, lengths, sequences, contacts, methods and materials are allowed; a violation rejects that assignment |
| Compactness | Length ceilings restrict the domain; traversal favors compact alternatives without proving a global minimum |
| Diversity objective | Which permitted alternatives receive search effort earlier; it does not waive constraints or award admission points |
| Computing limits | How much of the domain is explored now; unfinished work remains unresolved |
| Saving and filtering | Which recorded complete preparations are included or visible; an explicit query or identity list may select a subset |

The current construction preference contract has `ranking: none`. A longer
construction inside the declared bounds remains eligible. Search order can
affect which preparations are found in a bounded run, even when there is no
ranking of the resulting preparations.

Retained construction DNA, added pairing, loops and auxiliary handles measure
different things. Compare them at the intended molecular stage; see
[added stem and retained DNA](../language/ontology/molecular-meaning-and-search.md#added-stem-and-retained-dna).

The API fields `left_gap` and `right_gap` measure end-to-stem spacing on the released
insert: the paired positions between each sticky end and its supplied-stem
boundary. Zero puts that sticky end directly beside the stem. Two retains two
additional paired positions there. A gap is not missing DNA, a primer handle or
a loop extension. Sticky-end words and these distances are separate inputs.

Freezing a preparation collection includes all matching recorded preparations,
deduplicated by preparation identity. An explicit query or identity list can
capture a subset. See [saving preparations](../guides/share-atlas-edition.md) for
membership and molecular-map interpretation.

Use [survey scope and search](../reference/interface-survey-search.md) for
request bounds, traversal and completion semantics. The API, CLI and browser use
these same requests, choices and selections.

## What can you conclude?

Two preparations may differ in the foldback, basal association, released ends,
or only the materials used to make the same product. Count exact products at
the intended molecular stage and inspect preparation alternatives separately.
One geometry can contain several sequences; several preparations can produce
the same product.

Choose against your requirements first: available enzymes, permitted product
ends, pairing rules, and the materials you can supply or allow HOP to derive.
Then compare complete candidates using an explicit preference, such as less
retained construction sequence. An example's particular end sequence is not
a requirement for other designs. See the [construction guide](../guides/compile-construction.md)
for filtering, sorting, inspecting, and selecting alternatives.

A complete candidate satisfies its declared molecular requirements. HOP can find
it before the search is exhausted, so candidate completeness does not establish
exhaustive coverage or a shortest construction.

A successful computation supplies exact sequence and processing expectations.
[Verification](../provenance/overview.md) checks that the saved result follows
from its inputs. Before cloning, check the cohesive ends against the intended
destination.
