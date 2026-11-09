# What can vary while these properties stay fixed?

Run these repository examples from a [source checkout](install.md#work-from-source).
The commands use its locked environment throughout.

Explore complete molecular designs from a saved discovery or molecular-edit
result. Choose a neighborhood, inspect its supported variants, and filter the
complete products. Several preparations can produce one
product; several products can remain compatible with one neighborhood choice.

A **neighborhood** is a named molecular region: the loop, its closing paired
region, the open-side assembly region, the supplied stem or the later released
interfaces. A **product** is the molecule at the stage you inspect. A
**preparation** includes that molecule's exact input oligos and ordered
processing route. Choosing a local variant therefore means finding a complete
preparation that supports it together with your other requirements.

Run the [public example](../../examples/molecular-editing/conditional.py):

```bash
# Generate the saved result used by this conditional-exploration example.
uv run --locked python examples/molecular-editing/conditional.py /tmp/hop-conditional
uv run --locked hop-design construction edit-view /tmp/hop-conditional/alternatives --evaluated --out /tmp/hop-conditional-view
```

The example explicitly permits two basal nickases, two end placements and bounded
four-nucleotide loop exploration without supplying loop words. It retains failed
preparations and incomplete coverage. Inspect `all-choices/summary.json`,
`bsrdi-background/summary.json`, `btsi-comparison/summary.json` and
`selected/report.md`. The last directory includes exact oligos and portable
construction bundles. `preview/projection.svg` is a static molecular comparison.

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
respect recorded enzyme roles. Export
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

## Interpret the example's comparison

The examined Nb.BsrDI continuation fails for AACA; Nb.BtsI supplies a complete
AACA preparation but also changes retained stem sequence. It therefore does not
satisfy a reference fixed to Nb.BsrDI surroundings. Explicitly using the Nb.BtsI
AAAA reference admits both AAAA and AACA while preserving their non-loop sequence.

The result distinguishes complete compatible options, complete options excluded
by a control, failed examined preparations, local exhaustion and unfinished
coverage. Check the declared permissions before interpreting an absent option.

Inspection follows recorded ancestry and pairing. It reports when a focused
material has been removed or has not entered the displayed state yet; unassigned
regions remain explicit. Released overhang positions select **Released interfaces**
only at their actual endpoint. Opening a local chooser changes the explored
neighborhood without altering its permitted variants. Following a base inspects
ancestry. Arrow keys move between bases, Enter opens local choices and I follows
the focused address. The drawing shows recorded pairing.

## Continue with the task you need

[Explore and revise the construction envelope](explore-conditional-variants/construction-envelope.md)
to read parameter domains, evaluate a selected region or preview explicit
permission changes.

[Inspect variants through CLI and Python](explore-conditional-variants/cli-and-python.md)
to save a query, preview an exact preparation, follow base correspondence and
export its complete atlas. For a desired variant outside the evaluated pool,
use the existing [authored-edit workflow](edit-folded-sequences.md).
