# Molecular domain and auxiliary completion

Declare the permitted end pairs, geometry, methods and materials, then choose how
source-context alternatives are completed.

Return to the [interface survey search reference](../interface-survey-search.md).

## Declare the molecular domain

Author a `hop.interface-survey/v2` JSON or YAML document. It uses the same stem,
geometry, catalogue, material and molecular constraint definitions as a
[product request](../../guides/design-a-construction.md), with these differences:

| Field | Meaning |
| --- | --- |
| `targets: {}` | All 256 exact four-base words on each side, giving 65,536 ordered pairs |
| `targets.left_words`, `targets.right_words` | Optional explicit subsets; omit a side to retain all words; their Cartesian product is the declared target domain |
| `interfaces.left`, `interfaces.right` | Each word's `orientation` and `overhang_end`, read on its own protruding strand |
| `placements` | Joint `{left_bp, right_bp}` permissions; unlisted cross-pairings are not inferred |
| `foldback` | `geometry`, `enzymes`, and molecular `max_retained_overhead_nt` |
| `basal` | `geometry`, `enzymes`, `max_retained_overhead_nt`, and distinct positive `annealing_lengths_nt`; optional `end_footprint_pairing` |
| `release` | `enzymes` and a nonempty, distinct `basal_projections` roster; per-evaluation site-pair quota is supplied at execution |
| `source_context_objective` | `all_words` (default) or `paired_scaffold_completions`; defines which upstream-context alternatives must be enumerated |
| `preferred_source_contexts` | Optional set of up to 16 exact source-context words to try first within each protected scaffold group; requires `paired_scaffold_completions` and a constrained upstream domain |
| `source_handle_seed` | Optional exact DNA starting sequence for auxiliary source positions across all protected scaffold groups; requires `paired_scaffold_completions` and a constrained upstream domain |

Retain `stem_arm`, `enzyme_catalog`, `materialization`, `local_constraints`,
`preferences`, and `whole_route_constraints`. Omit product `endpoint`, `ends`,
`enumeration` and local `search` fields. The survey endpoint is fixed; target words
and joint placements derive each product's end requirements. Association lengths
have one authoring location: omit `basal.geometry.minimum_adapter_annealing_nt`.

Declare the recognition-site obligation separately from released-end geometry:

```json
"basal_projections": [
  {"product_end": "right", "recognition_material": "source_duplex"},
  {"product_end": "right", "recognition_material": "endpoint_material"}
]
```

Each branch uses exactly one declared projection. `source_duplex` requires the
local source to provide that recognition footprint. `endpoint_material` permits
the later material to provide it; it neither assigns the site to the adapter nor
creates a missing site. Exact copying, site placement and cleavage still replay
through the complete construction. A source-site obligation can couple the two
released gaps, so it must not be inherited silently from an example.

The query, selected trace, atlas and retrieved product request retain this
recognition-site obligation. The same release
enzyme still supplies both end-generation actions. V1 requests and checkpoints
require their original producer; rewriting their schema is not a migration.

Audit fixed oligos, source-primer spans, exact loop words, nick offsets, pairing
permissions and whole-hairpin requirements before starting. They remain hard
constraints; increasing a computing budget will not broaden them. Choose molecular
limits for your application; the shipped example supplies starting values only.

For an inclusive interval, declare every permitted integer rather than a few
representative lengths. The shared design-revision operation accepts, for
example, `{"parameters": [{"key": "adapter_annealing_min_nt", "minimum": 14,
"maximum": 24}]}`. This permits all eleven minimum annealing lengths; an
explicit `values` list remains exactly that subset. API, CLI and browser
permission editing use the same revision contract. Low-level saved requests
still store the resolved finite lists; old sparse requests are not silently
expanded. Left and right gaps are sticky-end-to-stem spacings on the released
insert, distinct from minimum adapter annealing and foldback join offsets.

Traversal reaches changes in the actual placement, arm, join, loop and strand
variables before exhausting a flattened roster. It also interleaves foldback and
basal sequence members with source contexts. This is an ordering preference:
every declared case remains reachable, including shorter primer-span estimates
and sparse joint placements. Saved canonical addresses retain their molecular
meaning; a changed producing implementation still requires a new checkpoint.

An upstream IUPAC context or length range remains a domain, not a request to use
only its first sequence. The survey addresses exact permitted assignments and
interleaves those continuations with local sequence alternatives. It visits the
first preferred assignment at each permitted upstream length before the second
at each length. When the selected local source supplies an exact placement frame,
contexts placing the requested left recognition site and end word are visited
first. Every other permitted context remains accessible; this ordering does not
prove complete-route compatibility or exclude a target. Adapter handles
remain exact under the existing material policy; primer range policies choose the
shortest permitted binding footprint. Those are explicit policy semantics, not
an exhaustive search over all possible auxiliary oligos.

### Complete handles without enumerating every interchangeable word

Set `source_context_objective: paired_scaffold_completions` when the question is
which paired scaffolds and released inserts can be prepared, rather than every
possible unpaired handle sequence. This preserves each local assignment, context
length and context sequence affecting basal pairing or the released insert. For
each such group and local pair, the executor seeks one complete preparation.
Exact unpaired hairpin sequence, primers and materials may differ. Use `all_words`
when those alternative sequences themselves are the subject of the search.

Grouping uses explicit coordinates that locate source bases, adapter contacts
and release cuts relative to one another. Where that coordinate frame cannot be
established, every context position stays protected.
Correlated sequence permissions remain correlated. Finding one witness ends
only that group's completion search; it does not remove other local sequences,
geometry or methods. Failing one handle does not exclude the group. Failed
attempts continue alongside other groups and local pairs so a large failing
handle domain cannot monopolize the search.

To reuse a useful handle as a starting sequence across scaffold choices, put
`source_handle_seed` in the survey or released-insert construction context:

```json
"source_context_objective": "paired_scaffold_completions",
"source_handle_seed": "CTTTGCAGTCGTAC"
```

The seed is read 5′ to 3′ from the start of the upstream source context. It
orders auxiliary completions by the number of substitutions from covered seed
bases, with A/C/G/T word order breaking ties. Protected positions remain determined
by the scaffold group and its coupled constraints. A shorter context uses only
the covered prefix; additional positions beyond the seed retain canonical order.
The seed does not select a length, add permitted bases, or require exact primer
reuse. Substitution distance orders
attempts within the existing preference tiers; a stopped search does not
establish the closest complete preparation.

The compiler checks the completed preparation. An active unintended site can
exclude its entire conflicting context pattern before the next completion is
attempted. The seed therefore remains useful when one of its bases must change
for a different method. A bounded attempt that has not found a valid completion
leaves that scaffold unresolved. Seed substitutions are auxiliary completion
choices, not additional scaffold-diversity targets.

To prioritize particular complete upstream words as well, supply their
words as `preferred_source_contexts` in the survey or released-insert construction
context. These words precede the other completions **within their existing
length and protected-sequence group**. They do not add permitted words, move a
scaffold ahead of other scaffolds, or change canonical sequence addresses. Words
outside the permitted domain or excluded by early molecular checks are not tried.
The complete compiler still checks primer binding, recognition sites, cleavage
and the final product. If a preferred word fails, the remaining permitted words
stay available. This is a search preference, not a requirement to reuse an exact
oligo; use the material-reuse contract when exact reuse is required.

Exact preferred words precede seeded completion within their admitted group.
The saved request binds both preferences, so changing either requires a new search
index. The same context works through `design discover`, the Python API and
subsequent atlas capture.

For the translated forward-left/reverse-right, five-prime release frame, the
executor first computes a compact relation between **both** end words for each
basal geometry and single permitted release method. This relation records which
pairs of end words can satisfy the necessary sequence constraints together.
Source/adapter pairing, recognition windows, copying and the noncanonical-pair budget constrain that
relation together. The same relation answers many exact end requests without
enumerating every end pair or every auxiliary handle word. Foldback geometry is
absent from this necessary end relation; full construction still tests it.

The executor admits this basal/end frame **before** expanding its foldback
alternatives. A contradictory frame therefore does not repeat for each loop,
arm and join case. Every admitted frame retains all authored foldbacks; if its
first complete construction fails, other permitted constructions remain
reachable. Navigation and frontier limits still apply, and a stopped search
remains unresolved. Existing checkpoints remain bound to their producing engine;
start a separate index for a changed producer.

Established joint relations are reused across requested end pairs within the
same bound request and limits. Recognition footprints first restrict their shared
base variables directly; paired-base relationships remain jointly enforced.
This avoids repeated request lowering and temporary sequence graphs while
preserving the permitted molecular space and complete compilation checks.
Selected atlas inspection and material retrieval reconstruct the same conditioned
candidate population used during discovery, without modifying the checkpoint.

Navigation records `end_pair_admission`. A rejected pair cannot satisfy the
translated conditions within that template. `permitted_pair_count` counts pair
assignments admitted by this necessary relation. Each still needs local and
complete construction verification. Unknown frames retain ordinary search,
and computation limits remain unresolved. This applies only to
`paired_scaffold_completions`; the public request syntax is unchanged.

For multiple requested end pairs, the executor can screen the complete basal
frame list once per invocation, group identical necessary relations and visit
only compatible or unresolved frames for each pair. It preserves their cost
order and every foldback alternative. A frame rejected by a necessary relation
does not consume a separate navigation step for every end pair. The resulting
`shared_end_pair_screen` reports frame count, unknown count, distinct relations
and the digest of the complete frame-to-relation mapping. These are screening
facts, not preparation counts; ordinary route checks still establish support.

The screen is bounded to 32,768 frames and 16 MiB of distinct serialized
relations. Requests exceeding either bound use ordinary navigation in full;
they are not truncated. A single-target request uses its direct path. Unknown
or resource-stopped frames remain candidates. Cooperative cancellation checks
between frames, and a partial screen cannot establish an exclusion. Cold resume
rebuilds the same screen before using it. This changes navigation work accounting
and does not authorize continuation of a checkpoint produced by an older engine.

Before grouping, the executor propagates the requested released ends and their
recognition windows back into the shared source/adapter sequence variables.
In the supported bottom-nick frame, this includes copied source bases, canonical
distal adapter pairing, and added adapter or endpoint-primer handles. Contradictory
local assignments or context lengths can therefore be skipped before complete
compilation. Alternative permitted release methods remain a union of joint
sequence possibilities. Fixed adapters, explicit distal pairing policies and
unproved coordinate frames retain ordinary evaluation.

The same constraints first restrict the whole joint basal population, before
selecting individual source/adapter pairs. The search asks whether any permitted
handle-base assignment works across the entire context domain. A short unsuccessful
completion does not eliminate a scaffold that permits a longer one. Correlated source
admission, contact classes and the noncanonical-pair limit remain enforced.
Surviving members keep their original exact sequence addresses.

Navigation records `endpoint_population_admission` separately from local basal
admission. Its counts describe necessary endpoint compatibility, including any
programs retained without translation. An empty conditioned population does not
mean that the local basal reaction is impossible, and it cannot create a local
empty-plane certificate. Complete preparations still require compiler witnesses.

Known recognition and end-footprint preferences then order surviving protected
groups and handle words. Preference alone is not an exclusion proof. The recorded
`release_context_admission` counts compare authored and admitted context domains
for the pages examined by each navigation step; these are not preparation counts.

An initial-source recognition conflict can rule out additional handle words
only when its exact site predicate has been derived in the same local frame.
All surviving words still pass ordinary complete compilation. Resource stops
remain unresolved. Progress and query results include `enumeration_scope`;
`all_preparations_enumerated` remains false for this completion objective even
after every group has been resolved. Changing the objective requires a new
request and checkpoint; it does not reinterpret an existing survey.

This survey requires one exact supplied stem. Interface coverage applies to that
stem and the declared route, geometry and material permissions.
