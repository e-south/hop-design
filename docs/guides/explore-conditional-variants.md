# What can vary while these properties stay fixed?

Explore complete molecular designs already supported by a saved discovery or
molecular-edit result. Choose a neighborhood, inspect its supported variants,
and narrow the whole products available. A local variant is never permission to
combine independently available parts. Several preparations can produce one
product; several products can remain compatible with one neighborhood choice.

Run the [public example](../../examples/molecular-editing/conditional.py):

```bash
# Generate the saved result used by this conditional-exploration example.
uv run --locked python examples/molecular-editing/conditional.py /tmp/hop-conditional
hop-design construction edit-view /tmp/hop-conditional/alternatives --evaluated --out /tmp/hop-conditional-view
```

The example explicitly permits two basal nickases, two end placements and bounded
four-nucleotide loop exploration without supplying loop words. It retains failed
preparations and incomplete coverage. Inspect `all-choices/summary.json`,
`bsrdi-background/summary.json`, `btsi-comparison/summary.json` and
`selected/report.md`. The last directory includes exact oligos and portable
construction authorities. `preview/projection.svg` is a static molecular comparison.
These are source-candidate operations; see [installation](install.md).

## Explore the construction envelope

The parallel-coordinate overview keeps the evaluated network visible while you
narrow it. Solid paths represent complete preparations; faint paths preserve
excluded context. Dashed segments represent verified **local** foldback or basal
realizations. They stop before unassessed axes and cannot be selected as complete
products. A local segment does not establish compatible surroundings or a completed
route. Crossings never authorize recombination.

Run the broader, bounded [construction-envelope request](../../examples/molecular-editing/construction-envelope.json):

```bash
# Discover scaffolds under the explicit construction envelope.
hop-design construction discover-scaffolds examples/molecular-editing/construction-envelope.json --out /tmp/hop-envelope
hop-design construction edit-view /tmp/hop-envelope --evaluated --out /tmp/hop-envelope-view
```

This public synthetic request fixes the receiving end words, permits paired
placements 6/6 and 0/0 bp and two basal nickases. Foldback arm and loop lengths
are free within a 32-nt retained-construction budget, with declared minima of 3 bp
and 3 nt. Join displacements span 0–16 nt; geometry and enzyme constraints still
exclude incompatible combinations. No loop-word shortlist is supplied. Four method/placement
branches each allow up to 40 local realizations and 40 continuations. These are
computation limits, not molecular restrictions. Early compact local candidates may
fail the retained 14-nt source-primer requirement. Those failures remain visible.
Remaining permissions stay visible even when no complete path reaches them. This is bounded
construction evidence, not a universal feasibility survey or a laboratory result.

### One vocabulary for the diagram, axes and query

Select a molecular feature to inspect its quantities, then expose the related
coordinates in the plot. Hover or keyboard-focus an axis to locate the quantity
and its dependencies in the teaching key and throughout the atlas. Parameter definitions
include symbol, units, molecular stage, measurement boundaries and dependencies.
See the [parameter and teaching-glyph coverage specification](../reference/molecular-parameters.md)
for the three coordinate frames and explicit nonspatial context.
For example, the self-paired arm is **R = A − D**. Brushing R constrains compatible
A/D pairs; it never makes R independently editable.

Each axis distinguishes its declared domain from the observed values. **Fixed by
request** means the request permits one value; **constant among evaluated results**
means the recorded preparations happen to agree. A requirement is not an achieved
measurement. In particular, required adapter annealing is a threshold; achieved
annealing counts the full recorded source/adapter association, not just the local
basal contact window.

The primer-boundary view connects a rejected continuation to its examined source:
the pale stem fill is retained, the available outside-stem flank has its own
bracket, and the required primer footprint shows why that continuation fails.
The diagram is source geometry, not a completed failed hairpin. Buttons beneath
it inspect complete alternatives from the same declared branch that also satisfy
the current selections; they do not claim a uniquely necessary repair.
Portable choice exports include `primer-boundaries.svg` and all individual
failure records in `choice_space.primer_boundaries`. The atlas separately locates
required primer footprints and available flanks on a complete preparation.
Zero-length measurements retain coincident boundary markers.

The short, wide plot fits the desktop viewport. Values sit directly on their axes
in rounded nodes; paths meet those nodes. At 1,200 px it can show all 24 loop words
in the open-envelope example. Height is capped at 368 px; denser domains prioritize
selected and supported labels while retaining every coordinate and path. Literal
values wrap rather than becoming indistinguishable ellipses. Focus and **Browse…**
provide remaining labels and the full domain. Resizing changes only presentation.

The default order connects foldback geometry, basal method and displacement,
released-end gaps and the source-primer span. Method and receiving-interface
permissions remain visible beside the plot, including fixed words and polarities.
Selecting an ordered source/adapter contact exposes its source base, adapter base
and contact class together. Positions count outward from ligation, beginning at
zero; these are recorded contacts, not predicted pairing probabilities.

**Return to molecular overview** leaves constraints and preview intact. Active
filters stay visible even when their axes are outside the current detail.
**All parameter meanings** provides every registry entry, including quantities
that are not applicable to the selected preparation. Composite method/background
identities open their full domain descriptions rather than dense, abbreviated
sequence columns. The teaching key is also exported as `teaching.svg`.

Drag the strip beside a numeric axis to select an inclusive, integer-snapped
range. Keyboard arrows move the interval; Shift plus arrows changes its upper
boundary; Escape clears it. Click categorical values to permit one or more
alternatives. Selections within an axis mean **OR**, and axes combine with **AND**.
Counts for each value hold all other axes and preserved properties fixed, omitting
only that axis's selection. Joint permissions still apply: 0/0 and 6/6 never
create a permitted 0/6 placement.

The browser saves these selections in the same `hop.scaffold-variant-query/v2`
used by CLI/API. It preserves the comparison reference and stage-qualified
controls. **Clear parameter selections** removes the axis selections explicitly.
Zero matching preparations means absence from the evaluated pool. It does not
establish global impossibility. Shared constants are disclosed once beneath the
plot; numerical intervals do not imply that every position has been evaluated.

### Evaluate a selected region explicitly

**Coverage and further bounded evaluation** distinguishes declared branch domains,
examined continuations and local exclusions from unexamined branches. Failed
continuations do not receive invented downstream coordinates. Achieved contact
counts and terminal dimensions can remain unassessed until a complete route exists.

Brushing only filters existing evidence. **Evaluate selected region** runs a new,
explicitly bounded evaluation under the active generating permissions intersected with the
selected parameters. Numeric and positional constraints narrow their owning local
generator where supported; remaining achieved-property controls are checked after
construction. Required panel targets outside the selected region stay recorded as outside this
evaluation round; they are not silently fulfilled or removed.
The operation does not guarantee a globally exhaustive or joint
search for a comparative family. Its packet retains the previous pool unchanged.
The union preserves original labels, deduplicates exact preparations and reapplies
the query; coverage counts evaluation records, which can overlap across rounds.

The equivalent file-oriented operation is:

```text
hop-design construction variants RESULT --query QUERY.json --out CHOICES
hop-design construction evaluate-parameters RESULT CHOICES --max-branches 4 --max-continuations 1 --out EXTENDED
```

The query needs the current `result_digest`, ordinary stage/focus fields and, for
example, `"parameters": [{"key": "self_paired_arm_bp", "minimum": 7, "maximum": 8}]`.
Reload `EXTENDED` and reissue the query with its new result digest. CLI/API use the
same immutable evidence as the browser. To expand a generating permission, use
the separate revision operation below.

### Browse unobserved values and revise the envelope

**Browse domain…** exposes permitted values even without a complete preparation.
For unfixed loop words, choose a length and step through A/C/G/T prefixes; no
manual sequence entry is needed. Integer pages retain holes in discrete domains.
Outlined values have no complete preparation recorded. Selecting one keeps every
other selection and preservation control, then permits targeted evaluation.
Values supported elsewhere in the pool show the conflicting axis selections and
an explicit **Use this recorded combination** action. It does not clear hard
preservation controls. Consult branch coverage for failed or unfinished evaluations.

**Revise generating permissions…** edits one named declaration at a time. Add
changes, preview the exact before/after values, resolve any reported conflicts,
then explicitly evaluate with branch and continuation budgets. The supplied stem,
receiving end words/polarity, material policies and query controls remain locked.
A preview is not a feasibility result. Permission to use an enzyme is not evidence
of laboratory availability.

For example, keep a selected R = 9 while changing an arm domain from 8–10 to 10–12
bp. The old domain supplies only A/D = 10/1; the revised domain can also test 11/2
and 12/3 when those D values are permitted. Arithmetic compatibility does not imply
molecular completion. This is an explicit revision, not a hidden relaxation.

```text
hop-design construction parameter-values RESULT CHOICES --parameter loop_word --length 4 --prefix AA --out VALUES
hop-design construction revise-envelope RESULT CHOICES REVISION.json --out PREVIEW
hop-design construction evaluate-envelope RESULT PREVIEW --max-branches 4 --max-continuations 4 --out EXTENDED
```

The executable [envelope example](../../examples/molecular-editing/envelope.py)
targets a new word and a derived arm length, previews explicit changes and saves
the refreshed choices for an explicit retrieval. Run it against the saved pool:

```bash
# Run the example that inspects unobserved values and a revised envelope.
uv run --locked python examples/molecular-editing/envelope.py /tmp/hop-envelope /tmp/hop-envelope-jump
```

An example revision removes a loop shortlist while retaining the current query:

```json
{
  "schema": "hop.scaffold-envelope-revision/v1",
  "changes": [{"path": "product.foldback.geometry.loop_sequences", "value": null}]
}
```

Empty arrays for `annealing_arm_lengths_bp` or `loop_lengths_nt` mean free within
construction bounds; join displacement arrays must remain explicit. Available
editable declarations are in `pool.envelope.fields`. A new evaluation packet retains
`previous/`, `additional/` and `preview/`. Reload it and bind the saved query to its
new result digest before retrieval. Subsequent evaluation uses the revised envelope.
Earlier preparations remain inspectable under their original request; narrowing
future permissions does not erase those historical results or silently filter them.

Select a whole path, or use **Preview preparation**, to inspect its exact route.
Overlapping paths require an explicit preparation choice. Exact products are counted
once while alternative preparations remain available. Processing state, camera and
comparison reference survive the change. A filtered-out preview remains labeled
as context until another preparation is deliberately previewed.

**Define a required set** opens a separate comparison: permitting either loop word
does not require both. It uses the current molecular query, including parameter
selections; filtering never silently selects preparations for retrieval.

The `choice_space` member of `query_scaffold_variants(...).json_bytes` contains
stage-qualified axes, declared domains, complete paths, local support, exact-product
groups and branch coverage. Its query scope is `admitted_pool_with_explicit_eligibility`;
`eligible_under_preserved_controls` distinguishes whole-pool context from paths
admitted by neighborhood pins and preservation controls. `compatible_options`
remains the authoritative filtered list. Previously saved choices must be
regenerated against their original pool after a projection change; never edit or
reseal historical packets. These projections introduce no new molecular authority.

## One complete route, local choices

Open the printed local address. **All processing steps** is the default: one
sequence-resolved atlas contains every recorded state and its material inputs.
The initial compatible preparation is a preview, never an implicit selection.
Click a molecular region to open its anchored chooser of observed sequences and
dimensions. Choosing one requests a complete compatible preparation immediately; it
does not change permitted variants. If several preparations support that choice,
choose a background explicitly. Method names and differing sequence words
label those backgrounds; preparation IDs remain in the exact records. Identical products do not collapse distinct preparations.

**Edit allowed choices and preserved properties** changes permissions explicitly.
**Define a required comparative set** specifies obligations. These operations are
separate from previewing. A fixed region has one preview action; an unavailable
region has no selectable sequence. Region labels report choices at the query's
assessment stage, which can differ from the displayed processing state.

Set a fixed comparison reference, then preserve sequence outside the loop,
pairing, chemistry or exact product identity at the intended molecular stage.
The reference remains fixed as variants change. The molecular differences precede
material differences; these are separate questions. Add explicit preparations to
the comparison set, choose its baseline, and retrieve. Members outside a later
query remain visible and block retrieval until you remove them or explicitly
revise the choices. The selected baseline does not replace the fixed exploration
reference.

The generating envelope above the atlas separates declared basal/foldback domains
and required dimensions from achieved hairpin properties. Its method permissions
respect recorded enzyme roles; they do not establish laboratory stock. Export
the captured request to author an explicit revision with `prepare-edit` and
review it before a separate `evaluate-edit` operation. Local browsing never
expands that envelope or launches search.

The hairpin view depicts the recorded pairing architecture. The endpoint view
depicts the actual preparation product. Released-insert interfaces are not
exposed ends on the hairpin intermediate. **Processing step** inspects the same
preparation without changing the query, reference, pins or selected membership.
Use **Follow this base through processing** in the local chooser, or press **I**
on a focused nucleotide, to follow recorded ancestry and pairing. This changes
only the inspected position. Unmapped positions remain explicit; matching letters
alone do not establish correspondence. SVG and exact-record links export the
atlas or isolated state. Returning to **All** restores its camera frame.

**Assess choices at** changes the query's molecular stage. That separate operation
requires explicitly clearing incompatible stage-qualified pins; preserved controls
retain their named stages. If a constraint edit excludes the preview, its identity stays recorded with an exclusion explanation; the viewport does not
show it as compatible. Choose a supported variant or explicitly revise permissions.

### Keep surroundings while exploring a region

With a complete preview displayed, **Keep surroundings of the current neighborhood**
fixes that preview as the reference and requires every other assessed neighborhood
to remain unchanged at the query stage. If a different reference is already fixed,
change it explicitly first. The equivalent query member is:

```json
"surroundings": [{"stage": "hairpin", "except_neighborhood": "loop"}]
```

Pass this in a complete `--query` document or the Python query dictionary together
with its `reference`. Unknown surroundings fail the requirement; equal missing
values do not count as evidence of preservation. Changing **Neighborhood** later
does not rewrite the control's stage or exception. Remove regional preservation
explicitly when a different comparison is intended.

Local choices follow the dependency order: neighborhood, observed variant, background
only when several remain. One chronological processing selector remains above the atlas. A pending
background choice can retain the previous drawing as clearly labeled context;
it supplies no retrieval target. Molecular picking is suspended during motion so
a moving base cannot be mistaken for its neighbor. Variant and state controls can
interrupt a transition; superseded responses do not replace the latest view.

Clicking a region never moves the camera. Drag or use ordinary trackpad scrolling
to pan; pinch or Ctrl+scroll to zoom at the pointer. With the viewport focused,
**+**/**−** zoom and **0** fits. The bottom-left **Fit route** control restores
all stages; isolated states offer **Fit molecule**. Hover or keyboard focus
emphasizes a region across the route and its recorded recognition/cut annotations.
Zoom changes only the camera. Pale red spans
mark the supplied stem; blue and green mark construction neighborhoods. Amber
spans mark recognition footprints. Position ambiguities remain next to the view;
uncolored positions in an unresolved region do not imply sequence equality.
Motion follows verified correspondence between recorded drawings and fades
unmapped parts. Reduced-motion preferences show the same static endpoints.

## Preview a local variant through CLI/API

Run the public browsing example against the same saved result:

```bash
# Preview one alternative without committing a new selection.
uv run --locked python examples/molecular-editing/browsing.py /tmp/hop-conditional/alternatives /tmp/hop-browsing --word AAAC --state cleaved_duplex
```

Read `preview/summary.json`. `preparation_choice_required` lists exact candidates;
rerun into a new directory with `--option` and a displayed candidate label. The
variant, constraints and processing phase remain explicit. `--state` accepts a
semantic phase, `all`, `hairpin`, `endpoint`, `source_material`, or an exact state ID.
A missing or ambiguous phase returns a named outcome with no substitute drawing.

```text
hop-design construction preview-variant RESULT CHOICES --variant VARIANT_ID --state cleaved_duplex --out NEW
```

Add `--option OPTION` to resolve a preparation explicitly. Optional `--focus`
contains an exact molecular address and requires `--focus-option` naming its
originating preparation. Across preparations, focus transfers only through a
unique recorded material identity and coordinate by default. `--focus-mode comparison`
also permits an unambiguous, region-bound comparison position when its material
ancestry changes. The response distinguishes `comparison_position` from
`shared_material`; neither changes a molecular record. Unresolved correspondence
clears the position with an explanation. Sequence similarity alone is insufficient.

Use `--view-from previous.json` to request transition correspondence. That file
contains `option_label` and `state` for the preceding drawing. The Python request
has the same `view_from` object and `focus_mode` field. `transition.links` separates
`retained`, `copied` and `comparison` relationships; unmapped addresses and notices
remain explicit. No interpolated frame is a molecular state or a reaction prediction.

Nicked and associated fragment drawings align recorded pairings while preserving
covalent breaks. Rounded translucent spans mark recorded enzyme recognition
footprints throughout the recorded route, independently of active cuts. Their
presence can be complete, partial, not yet present, removed or unresolved. A
footprint traces bases from a recorded recognition span; it does not establish
that the displayed substrate is cleavable. Active operation outlines and dashed
strand-specific cuts remain stage-bound: pre-cleavage marks are planned;
post-cleavage nick marks are applied.
Released insert views show achieved end-to-stem gaps separately from recognition
sites. None of these views implies a predicted conformation.

## Export the complete atlas

```text
hop-design construction atlas RESULT CHOICES --option OPTION --out NEW
```

The browser and `preview-variant` CLI default to `all`; Python preview requests
retain their `hairpin` default, so pass `"state": "all"` explicitly. An all-state
response supplies `inspection.atlas` and `atlas_transitions`. The separate
`inspect_scaffold_atlas(pool, choices, request)` operation takes result/query
digests and one `option_label`, plus an optional exact `focus`. It exports the
same `projection.svg`, captured `request.json` and exact atlas record. Occurrences
are preparation/state/strand/index tuples. Recorded ancestry and verified
cross-variant correspondence remain distinct relations.

The atlas aligns the supplied stem across states and marks changed inputs beside
their recorded uses. Primer arrows annotate recorded binding spans; an input
that binds a derived complementary template is identified explicitly rather than
drawn as a separate annealed state. Unpaired handles use schematic 45° branches;
noncanonical contacts retain their distinct pairing marks. Every base remains in
the vector scene, although overview text requires zoom for nucleotide reading.

## Require a controlled comparison

Allowing AAAA or AACA does not require both. Under **Require a comparison**, choose
each required loop from the observed choices, specify whether sequence outside
the loop must remain shared, then find compatible sets. This uses the current
query and keeps shared released interfaces. It does not silently remove pins,
change the reference or choose a different background for you. To discover
backgrounds without a reference, start with no reference and no reference controls.

The viewer examines at most 256 assignments and lists at most 16 sets, reporting
unexamined assignments. CLI/API requests supply their own explicit bounds.
Choose a displayed set and a presentation baseline, inspect either member, then
retrieve that required set. Retrieval rechecks every required member, molecular
control and material requirement against freshly admitted sources.

Run the equivalent public API example against the result above:

```bash
# Assess the requested controlled comparison.
uv run --locked python examples/molecular-editing/navigation.py /tmp/hop-conditional/alternatives /tmp/hop-navigation
```

Read `comparison/summary.json`. Then name a displayed set explicitly in a new output:

```bash
# Run the same comparison with the alternative example inputs.
uv run --locked python examples/molecular-editing/navigation.py /tmp/hop-conditional/alternatives /tmp/hop-navigation-selected --select-set set-0001
```

The example requires AAAA and AACA with shared non-loop sequence and released
interfaces. `states/` follows a pinned AACA preparation through all recorded states;
`selected/` contains both portable preparations. The pins used for inspection do
not replace the two-member comparison request.

Browsing never starts search. Adding a new loop word, permitting another method,
expanding coverage and relaxing a preserved requirement are separate decisions.
Use the [authored-edit operations](edit-folded-sequences.md) when your desired
variant is absent. A negative query means no compatible option in the evaluated
pool, not that the molecule cannot be made.

## The same choice model through CLI and Python

```bash
# Query conditional choices from the recorded result.
hop-design construction variants /tmp/hop-conditional/alternatives --stage hairpin --focus loop --out /tmp/hop-choices
```

The packet contains `query.json`, `summary.json` and a short report. A query has
an exact `result_digest`, `stage`, `focus`, optional fixed `reference`, `pins`,
`controls` and `surroundings`. Supported neighborhoods are `loop`, `closing`, `assembly`, `stem`
and `interfaces`. A variant describes the observed regional sequence, pairing
contacts and relevant termini; it names supporting complete options.

For an explicit control, use `--reference OPTION` and repeat
`--preserve hairpin:non_loop_sequences` or another stage/property pair. To reuse
or refine exact selections, pass `--query query.json` instead of those flags.
Each pin has one `neighborhood` and an array of allowed `variant_ids` taken from
the admitted result. Values within a pin are alternatives; different pins must
all hold together. A replacement query omits **only the focused pin** when listing
its alternatives. `compatible_options` still enforces every active pin.

```python
# Use the same recorded result and choice model through Python.
import json
from hop_design import construction

pool = construction.load_scaffold_exploration("/tmp/hop-conditional/alternatives")
choices = construction.query_scaffold_variants(
    pool,
    {
        "result_digest": pool.result_digest,
        "stage": "hairpin",
        "focus": "loop",
    },
)
print(json.loads(choices.json_bytes)["variants"])
```

Keep `pool` in memory for repeated queries. Admission replays the captured result
once. Queries use immutable facts without search, replay or report generation.
Reports are created on export; molecular drawings are separate projections.
Retrieval re-admits the source and re-derives the query before selecting:

```text
hop-design construction select-variants RESULT CHOICES --member NAME=OPTION --baseline NAME --out NEW
```

Repeat `--member` to specify the set. Python uses
`select_scaffold_variants(result, choices, members={name: option_label}, baseline=name)`.
Passing valid labels cannot bypass active pins or controls. A selection includes
`exploration-query.json` and `exploration-selection.json`, preserving the result,
reference and query identities. Molecular authorities remain in the portable set;
the query is decision provenance, not an additional chemistry authority.

## Interpret the example's comparison

The examined Nb.BsrDI continuation fails for AACA; Nb.BtsI supplies a complete
AACA preparation but also changes retained stem sequence. It therefore does not
satisfy a reference fixed to Nb.BsrDI surroundings. Explicitly using the Nb.BtsI
AAAA reference admits both AAAA and AACA while preserving their non-loop sequence.

The result distinguishes complete compatible options, complete options excluded
by a control, failed examined preparations, local exhaustion and unfinished
coverage. Unpermitted possibilities have not been tested. None of these records
establish laboratory recovery, destination compatibility or biological effects.

Inspection follows recorded ancestry and pairing. It reports when a focused
material has been removed or has not entered the displayed state yet; unassigned
regions remain explicit. Released overhang positions select **Released interfaces**
only at their actual endpoint. Opening a local chooser changes the explored
neighborhood without altering its permitted variants. Following a base inspects
ancestry. Arrow keys move between bases, Enter opens local choices and I follows
the focused address. The drawing represents
recorded pairing, not predicted conformation.

### Read the complete route

The atlas places the early processing stages down two columns, then centers the
hairpin-PCR duplex and released insert below them. Follow the numbered stages
down the left column, continue at the top of the right column, then read the
full-width finish. A direct hairpin route ends at its recorded hairpin state.

Unpaired handles bend away from the stem, then continue parallel to it. The
five-spacing bend is a drawing convention. Denatured fragments retain their
precursor registration with a small displacement; the drawing does not add
pairing contacts. Stage titles, enzyme names and termini use larger text while
nucleotide spacing remains unchanged.

`projection.svg` is the interactive overview. `projection.pdf` and `pages/` use
seven-inch pages with bases at least 8 pt, annotations at least 9 pt and labeled
continuations for wide scenes. Every base keeps its original molecular address;
view breaks are not cuts. Print at 100%. `print-layout.json` records the panel
boundaries and base ranges. Exact sequence and material
comparisons, when requested, are in `comparison.svg` and the packet summary.
The route retains their base highlights and correspondence warning.
