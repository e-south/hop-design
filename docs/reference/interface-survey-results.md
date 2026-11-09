# Interface survey queries, selections and exports

Use the [construction guide](../guides/survey-interfaces.md) for the runnable
workflow. This reference defines how its results relate to each other.

## Coverage and inspection

`construction survey inspect REQUEST --index FILE --limit N` returns evaluations
and coverage after checking index integrity. Its `next_offset` gives the next
page. Target addresses follow lexicographic A/C/G/T word order, left side first;
`step` is the committed evaluation ordinal within that target.

`construction survey verify REQUEST --index FILE` replays every recorded
evaluation without changing the checkpoint. Use replayed coverage for aggregate
molecular claims. Support for all 256 words on each side does not establish all
65,536 ordered pairs. Found preparations also do not establish a global minimum
of added DNA. See [search scope](interface-survey-search.md) for the three kinds
of coverage and the meaning of exclusions.

## Conditional queries

A query filters complete recorded preparations. It retains declared words,
placements, geometry and methods even where no complete witness exists.

| Result | Interpretation |
| --- | --- |
| Matching path | Satisfies every predicate in the query |
| Node's conditional count | Applies predicates on the other axes, showing what remains if this axis changes |
| `supported_elsewhere` | Has a complete witness outside the current conditions |
| `unresolved` | No witness or complete exclusion in the recorded search |
| Excluded within scope | Exhaustion establishes absence under the declared molecular permissions |

An end word can be excluded before the whole survey is finished: every declared
partner pair for that word must have a scoped exhaustion proof, with none
supported. Other axis values require whole-survey exhaustion to establish
exclusion. One excluded pair alone does not exclude either end word. Use
`inspect` for that individual pair's outcome.

Preparation counts deduplicate exact identities; record counts retain repeated
evaluations. Two preparations producing the same exact product remain separate
preparation choices. Crossing lines or individually supported axis values do not
license new combinations: only complete paths establish joint support.

`load_interface_survey_choices()` loads one immutable snapshot. Retain this pool
for repeated in-memory queries; load it again to see appended evaluations.
The snapshot digest changes with recorded evaluation history, while the query
digest changes with predicates. File-oriented queries load the index anew.

## Exact selections and sampling

A selection binds the request, recorded target and step, exact preparation
identity, query and snapshot. Selection fails if the path does not match.
Atlas inspection and retrieval independently replay that preparation.

`sample` chooses among distinct matching preparation identities. Repeated
records of one identity do not give it greater weight. The same seed, snapshot
and query reproduce the same selection. Expanding the pool can change the draw.
No match returns an error without further search or relaxed requirements.

An unchanged exact selection remains usable for inspection and retrieval after
new evaluations are appended. Its snapshot digest describes when it was made.
To plot the expanded landscape, select again against the newly loaded pool;
figure export requires the selection and figure to share a snapshot. If a
separate query accompanies a figure selection, it must agree exactly.

## Parameter key and landscape

`pool.parameter_key()` supplies the request's complete parameter definitions before
selection. The primary teaching strip shows locatable product features: basal
pairing and tails, loop-side extension and loop, then released ends and gaps.
The strip is schematic, not to scale. `parameter-guide.md` explains the remaining
construction quantities, their molecular stages and dependencies.

Figure export and the browser use the same projection. Product features and varying
methods lead; an active construction constraint adds its axis. Equivalent arm
measurements share one axis. Fixed requirements appear as context, while a wider
domain with only one observed value keeps its axis. Quantities known only from
completed records move to separate “constant in recorded preparations” context
when they do not vary; this does not make them requirements. Enzyme names remain literal.
Dense axes retain every recorded mark, prioritizing selected and supported labels;
hover or keyboard focus reveals exact values. Dense categorical axes place
witnessed categories first and reserve a tick for every remaining permission.
Their spacing expresses no numerical distance and stays stable under filtering.
Blue marks identify query constraints. Colored region bands connect the axes to
the basal, foldback and released-insert frames in the teaching strip.

The caption counts exact preparations and distinct projected paths separately.
Overlapping paths retain their complete membership. `domains.csv` keeps full
labels and support counts; `choices.json` retains every path and domain. Sequence
words longer than sixteen bases use length labels with exact words in the printed
key. Position-specific and composite predicates remain in the query record.
Export checks snapshot integrity; aggregate molecular replay is separate.

## Atlas, comparison and parts

The atlas contains recorded nucleotide states, primer and adapter inputs,
transition correspondence and parameter locations. It adds no inferred reaction
states. `projection.svg` is the full route; `teaching.svg` explains the selected
construction's dimensions. `parameter-key.svg` explains the request independently.

`projection.pdf` and `pages/*.svg` use seven-inch pages with nucleotide text at
least 8 pt and annotations at least 9 pt. Wide scenes continue in labeled panels;
these view breaks do not represent molecular cuts. `print-layout.json` records
each panel's native coordinate window, original base ranges and page membership.
Print at 100% to preserve those sizes.

`teaching.svg` shows the selected hairpin with its recognition footprints and
structural measurements. An insert preparation also shows the released insert
for its end words and gaps. Source duplex and adapter-association scenes remain
in the full route below.
Every base of the displayed structures is retained. Its readable
print counterpart is `teaching.pdf`, with continuation metadata in
`teaching-layout.json`. A selected choice-figure export includes these same
teaching files; an unselected export uses the general parameter definition key.

The primary panel uses `overview.svg`: one compact hairpin above the coordinate
plot, with no continuation rows, stacked insert scene or teaching camera.
Recognition footprints stay visible. Release-end words and gaps map through
recorded ancestry onto this hairpin and remain labeled as later release
coordinates. Translucent polygons connect each located feature to its plotted
axis. Changing the selected trace updates this same drawing and the full route.
The detailed measurement pages supplement this panel; they do not replace it.

An optional reference selection is independently replayed. The comparison marks
verified substitutions and regional additions across their recorded ancestry.
Dashed amber marks indicate unresolved correspondence; unmapped bases are not
therefore insertions or deletions. Existing regional correspondence takes priority
over whole-strand display alignment. Exact regional and endpoint sequences,
changed materials and terminal chemistry remain in `summary.json`.

An insert can differ while its earlier hairpin and basal contacts remain identical,
for example through changed PCR-primer tails or release boundaries. Those edit
marks belong to the endpoint. The packet preserves both selections; comparison
changes neither the selected preparation nor the reference's query eligibility.

Retrieval writes `selection.json`, `construction/`, `product-request.json` and
`preparation/`, including `oligos.csv` and the molecular trajectory. It requires a
new destination and works after relocating the request and checkpoint.

## Browser continuity

Changing preparations compares the new route with the previous one. Repeated
selection, filtering and checkpoint reload preserve the comparison. The camera
follows an unambiguous base correspondence at its current zoom; otherwise it
uses a uniquely matched processing stage. **Fit route** restores the full view.

Clicking an axis value replaces that axis predicate. Typed queries can permit
multiple values. Coincident paths keep their preparation identities, and an
excluded preview cannot be retrieved as a match. Atlas replay can take longer
than filtering the loaded coordinate pool. Search expansion and requirement
changes use the request and evaluation commands, outside the browser.
