# Molecular parameter and teaching-glyph coverage

The registry in `models/construction/variants/parameters.py` defines parameter names.
Its `ParameterDefinition` contract records molecular stage, units, role, drawing
frame, representation, boundaries and dependencies. `canonical_key` identifies a
single measurement across equivalent keys. `design_role` separates product
features, construction choices, outcomes and comparison context. This presentation
role does not grant edit permission: loop size is both a product feature and a
derived count. `choice_space.axes` adds the
captured request domain and observed values. Neither an axis nor a drawing grants
permission to combine independently available parts.

The opening plot teaches product features in plain language. The full registry
remains available through API explanations, the exported parameter guide and
domain records. Changing the displayed axes does not change query eligibility,
search coverage, product identity or preparation membership.

At the public `DesignChoices` boundary, method predicates accept the same permitted
canonical enzyme names and catalog IDs as a construction intent. Name resolution
uses the saved context, not the current set of successful witnesses. Ambiguous
names require an exact ID; unknown or unpermitted names reject. Resolved IDs feed
query, selection, sampling and figure export consistently. Query results expose
both `submitted_query` and resolved `query`.

Predicates over registered equivalent measurements apply together. Their common
domain must be nonempty; a contradiction identifies the declarations before any
pool filtering. Compatible predicates retain their original keys and bounds so
existing saved selection queries remain verifiable. This does not equate derived
or correlated quantities: a loop word and its length, an annealing minimum and
achieved contacts, or measurements at different molecular stages remain distinct.

The three-frame teaching key locates measurements and explains primer boundaries
for the selected preparation. The browser uses
the same `teaching.svg` as the portable atlas and single-state inspection exports.
The implementation state is recorded in the [roadmap](../dev/plans/roadmap.md#molecular-organization-of-conditional-exploration).

## Source and association frame

| Registry coordinate | Required drawing meaning |
| --- | --- |
| `basal_nick_offset_nt` (`n`) | Strand-specific basal nick boundary to supplied-stem boundary in the source duplex. A zero value keeps both boundary anchors. |
| `basal_strand`, `foldback_strand` | Nicked strand in the declared source coordinate frame, with 5′/3′ directions. They are not arbitrary top/bottom screen positions. |
| `basal_method`, `foldback_method` | Distinct recognition occurrences and strand-specific nick boundaries, with orientation and recognition-to-cut offsets. Presence is separate from activity. |
| `source_forward_primer_required_nt`, `source_reverse_primer_required_nt` | Required primer footprint measured inward from the appropriate source terminus. A constrained primer policy uses its shortest permitted annealing length. |
| `source_forward_primer_available_nt`, `source_reverse_primer_available_nt` | Full source flank outside the supplied stem. A successful primer may occupy less than this span. |
| `adapter_annealing_min_nt` | Minimum requirement from the ligation side, drawn as a threshold. It is not a count of every achieved contact. |
| `adapter_annealing_achieved_nt` | Full recorded association, including permitted noncanonical contacts. The local basal constraint window can be smaller. |
| `basal_source_base_i`, `basal_adapter_base_i`, `basal_pair_class_i` | One ordered paired-sequence strip. Position `i` counts outward from ligation, beginning at zero. A position exposes its three linked facts together. |

Show exact primer-binding footprints and copying direction. If a binding is
recorded on a derived complementary template, label that context rather than
inventing an additional annealed state. Distinguish unpaired handles from recorded
noncanonical contacts. A failed primer continuation can show its examined source
and requested footprint; it has no completed-product identity or later states.

## Folded-hairpin frame

| Registry coordinate | Required drawing meaning |
| --- | --- |
| `foldback_arm_bp` (`A`) | Supplied-stem boundary to loop boundary on both opposing arms. |
| `join_offset_nt` (`D`) | Supplied-stem boundary to the recorded foldback join; preserve the covalent boundary. |
| `self_paired_arm_bp` (`R`) | Join to loop boundary; `R = A − D`, not another independent degree of freedom. |
| `loop_word`, `loop_nt` (`C`) | Literal, countable loop bases in strand direction; `C = length(loop word)`. |
| `loop_side_paired_bp` | Same measured span as A for this construction; show the equivalence rather than a second independent control. |
| `open_side_paired_positions` | Recorded open-side contacts beyond the supplied stem. It is an achieved extent, distinct from an adapter minimum. |
| `noncanonical_pairs` | Locate the relevant recorded contacts and their classes. Zero is an empty contact set, not an absent measurement. |
| `five_prime_unpaired_nt`, `three_prime_unpaired_nt` | Separate terminal tails, each measured between its terminus and first/last contact. Zero-length tails retain the terminal boundary. |

Keep the supplied stem aligned and visually quiet. Loop-side additions, open-side
contacts, joins and unpaired tails have distinct locations. A choice highlights
actual sequence changes and their verified correspondence; an ambiguous alignment
does not justify animated positional identity.

## Released-insert frame

| Registry coordinate | Required drawing meaning |
| --- | --- |
| `left_end_word`, `right_end_word` | Literal sticky word on its own protruding strand, read 5′→3′. |
| `left_end_polarity`, `right_end_polarity` | Which terminus protrudes; screen orientation is not polarity. |
| `left_gap`, `right_gap` | Paired released-end boundary to the corresponding supplied-stem boundary. Zero uses coincident anchors. |
| `release_method` | Type IIS recognition footprints and both strand-specific cuts on recorded precursor states. Removed footprints retain their context; a released end does not imply the site remains present. |

Show copied stem context and the actual endpoint. Joint permitted placements are
tuples: permitting 0/0 and 6/6 does not permit 0/6. A v6 `receiving_end_pairs` roster
also preserves words, orientation and polarity together. Receiving words remain
locked unless that explicit request authorizes alternatives. Marginal axis values
never authorize crossed end-pair combinations.

## Context outside nucleotide intervals

`background` is a stage-qualified comparison of regional sequence, contacts and
terminal chemistry. `methods` is a composite preparation identity; individual
method-role coordinates provide the molecular explanation. Neither is another
nucleotide length. Preparation budgets, material-reuse policies, preservation
requirements and evaluation coverage remain contextual annotations, linked to
their exact declarations rather than drawn as molecular brackets.

Keep four evidence levels distinct: declared permission, recorded local support,
scoped rejected continuation and complete preparation. A value can have complete
support in one continuation and fail in another. An unexamined permission is not
a failure. Request-fixed and observed-constant are also different properties.

## Shared projection and rendering responsibilities

`parameter_locations` contains exact reference addresses, their ancestry-linked
occurrences and `boundary_anchors`. Thresholds and zero extents use anchors even
when a span highlight would be misleading. The atlas renderer supplies those
same locations to static SVG and browser highlighting. A teaching diagram must
identify its coordinate frame; it must not silently reuse a source interval as
a retained-product interval.

`teaching` is a `hop.parameter-teaching/v1` projection bound to the selected
materialized preparation. Each parameter supplies its definition, value, declared
domain and coverage kind. `location_key` references the enclosing
`parameter_locations`; contextual parameters have no molecular location. Frame
facts include source sites and cuts, ordered association contacts, hairpin
anatomy and released interfaces. The projection does not duplicate the full
molecular state or ancestry graph.

The selected `teaching.svg` renders every base, including both supplied-stem
copies, from the atlas's addressed states. Its `scenes` list references source,
association, folded hairpin and applicable released-insert states. Long scenes
continue on explicitly labeled rows; no sequence is abbreviated or re-derived.
`teaching.pdf`, `teaching-pages/*.svg` and `teaching-layout.json` retain these
occurrences on seven-inch pages at the same physical type sizes as the route.
A hairpin endpoint has no invented released-insert scene.

Browser teaching and route drawings load together before either is replaced.
The centered column is capped at 1,120 px. A fixed-height teaching frame keeps
the plot and route stationary across selections; scrolling reveals continuation
rows at readable base size and retains the inspected scroll position. This
display frame needs no replay or rendering of unselected preparations.

The effective requirement in one translated preparation can be stricter than the
initial request. For example, an 18-position scaffold requirement can raise an
adapter minimum originally declared as 17 nt to 18 nt. The key labels the
effective threshold and original requested value separately. Neither is inferred
from the achieved contact count.

The plot describes compatibility among complete preparations. The route describes
processing chronology. Hover/focus locates a quantity and its dependencies;
brushing filters recorded alternatives; selecting a complete path changes the
preview. Camera movement changes neither the request nor preparation identity.

## Compose a parameter figure

Start with the choices and selection from the [discovery guide](../guides/discover-designs.md).

Choose the displayed axes without filtering the preparation pool:
`choices.figure(selection=selected, display_axes=("left_gap", "right_gap", "foldback_arm_bp", "loop_nt"))`.
Use `choices.parameters(query=query)` or
`hop-design design parameters designs --query query.json` to read a feature's
meaning, active constraints and available operations. For example, loop size has
permitted lengths. Self-paired arm length follows from the arm and join position.
Left and right end gaps are revised together. A saved collection can be filtered,
while permission changes belong to its discovery request. Reading this guide to
the features does not run a search or verify preserved surroundings.

Requested constant coordinates remain visible. Unavailable,
inapplicable, repeated or noncanonical keys produce an error.

`display-projection.json` records displayed and omitted axes. `choices.json` and
`domains.csv` retain the complete coordinate data. Paths that coincide in the
drawing retain all their preparation identities. This changes figure composition,
not requirements, search or selection. It also applies to
the linked trace of a selected similarity or family figure. The exact route and oligo
handoff continue to use the same selection.
For an export-only recipe, pass the recorded axes again. To keep that composition
when reopening the browser or reproducing a figure, save it with the selection:

```python
# Save the axis order with this view for later inspection and export.
view = choices.view(
    selected,
    presentation={
        "landscape": "parameters",
        "display_axes": ["left_gap", "right_gap", "foldback_arm_bp", "loop_nt"],
    },
)
choices.figure(selection=view).write("compact-choice-figure")
```

The saved view retains the ordered axes. Browser hover, pinning and export use
that same recipe. Older saved views retain their original display defaults.
