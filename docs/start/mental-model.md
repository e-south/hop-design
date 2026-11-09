# From payload to hairpin construction

Start with the duplex sequence you want the hairpin to present. That payload
stays fixed while HOP searches the surrounding sequence and enzyme arrangements.
You can inspect where a junction is possible, what bases and cuts it requires,
and whether selected junctions can be completed into the requested product.

## What do you specify?

Author one payload arm as exact DNA or fixed and degenerate positions. HOP
derives its complementary arm. Compiling this anatomy gives the intended hairpin
sequence. To obtain a construction procedure, continue with discovery.
See [substrate spaces](../guides/substrate-spaces.md).

For construction, start with the stem and intended product using
[design discovery](../guides/discover-designs.md). End words, scaffold properties
and methods are optional constraints. A versioned context declares the available
enzymes, geometry and material permissions. Inspect or replace it as needed.
The physical starting material
is a source ssDNA oligo with construction flanks around the payload. Its sequence
and required auxiliaries depend on the chosen route.

The foldback neighborhood supplies the sequence that can be exposed, folded,
and joined to close the cap. The basal construction neighborhood supplies the
opposite junction, including adapter pairing and later end generation when required.
Neither search changes the payload.

## How do local junctions become a construction?

A local solution describes a possible junction. Composition checks selected
junctions together with the source, adapters,
primers, fragment removal and endpoint requirements. A construction fails if
required annealing sequence is missing or its materials are incompatible.

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
A direct ssDNA hairpin does not acquire adapter, PCR, or end-generation
requirements merely because another endpoint needs them. For material and
request examples, use the [construction guide](../guides/compile-construction.md)
or [check a named method](../guides/resolve-production-method.md).

## What can the search change?

HOP solves and reuses foldback and basal sequence domains separately. Within each
neighborhood, geometry, recognition sites, cleavage and sequence must agree. It
then checks selected combinations against the complete preparation's shared
requirements.

For adapter-bearing routes, **basal association** means the source–adapter contact
region. It is narrower than the whole upstream construction flank. The source-side
and adapter-side unpaired handles extend beyond that
association and provide homology for hairpin PCR. A source-side sequence can also
serve an earlier source-PCR primer. These are uses of the same bases at
different steps. Permitted mismatches belong to the association record, not the unpaired
handles.

The scaffold-completion search seeks a working auxiliary completion for each
scaffold assignment, rather than every interchangeable PCR handle. Bases that contribute to association or a retained product stay
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
to the coupled basal problem. Its unpaired handle has a different role. A primer
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
where the relevant enzyme acts. A later adapter cannot supply a site required
in the initial source duplex.

Searches explore increasing retained non-payload sequence. An existence search
keeps a witness for each accessible work unit. An all-realizations search keeps
every exact alternative within its reported coverage. A truncated search leaves
part of the declared space unresolved. See [search interpretation](../discovery/overview.md).

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

Retained construction DNA, added pairing, loops and auxiliary handles describe
different quantities. Compare them at the intended molecular stage; see the
[construction vocabulary](../language/ontology.md#payload-centered-construction-vocabulary).

The API fields `left_gap` and `right_gap` measure end-to-stem spacing on the released
insert: the paired positions between each sticky end and its supplied-stem
boundary. Zero puts that sticky end directly beside the stem. Two retains two
additional paired positions there. A gap is not missing DNA, a primer handle or
a loop extension. Sticky-end words and these distances are separate inputs.

Freezing a preparation collection includes all matching recorded preparations,
deduplicated by preparation identity. An explicit query or identity list can
capture a subset.
See [saving preparations](../guides/share-atlas-edition.md) for membership and
molecular-map interpretation.

Use [survey scope and search](../reference/interface-survey-search.md) for
request bounds, traversal and completion semantics. The API, CLI and browser use
these same requests, choices and selections.

## What can you conclude?

Separate local variation from complete combinations. Two preparations may differ
in the foldback, the basal association, their released ends, or only the materials
used to make the same product. Count exact products at the intended molecular
stage, and inspect preparation alternatives separately: one geometry can contain
several sequences, and several preparations can produce the same product.

Choose against your requirements first: available enzymes, permitted product
ends, pairing rules, and the materials you can supply or allow HOP to derive.
Then compare complete candidates using an explicit preference, such as less
retained construction sequence. An example's particular end sequence is not
a requirement for other designs. See the [construction guide](../guides/compile-construction.md)
for filtering, sorting, inspecting, and selecting alternatives.

A complete candidate can be found before a search is exhausted. Its completion
means that its declared molecular requirements are satisfied. It does not mean
that every alternative was examined or that this candidate is the shortest.
Keep the candidate's completeness separate from the search's coverage.

A successful computation supplies exact sequence and processing expectations.
[Verification](../provenance/overview.md) checks that the saved result follows
from its inputs. Before cloning, check the cohesive ends against the intended
destination.
