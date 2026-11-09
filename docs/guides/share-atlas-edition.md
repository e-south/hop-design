# Share an inspectable molecular atlas

An atlas edition captures complete preparations from a saved discovery. It carries
their exact material handoffs and original producer identity. It can retain the
original drawings or draw the selected molecule when inspected.
You can move the directory and inspect it without rerunning the search.

## Capture the choices you want to share

Start with a saved [discovery](discover-designs.md) containing at least one
complete preparation.

```bash
# Capture and query the currently recorded preparations.
hop-design design freeze designs --out atlas-edition
hop-design design query atlas-edition --format text

# Inspect its molecules and material handoffs in the local viewer.
hop-design design view atlas-edition --out atlas-view
```

Open the printed local address to explore the saved edition.

Freezing includes all matching recorded preparations. Use `--query query.json` to
capture a filtered set, or repeat `--identity ID` to name particular preparations.
The destination must be new and outside the discovery directory. The edition
records how many preparations it captures and how many matched in its source.

Ordinary capture uses the producer that can admit the discovery. Once captured,
an edition can be viewed independently of changes to that producer. A changed
renderer does not make an old live checkpoint compatible with a new compiler.

For larger collections, use compact capture. To fit the map, first
[install the atlas extra](install.md#fit-a-new-molecular-map). Viewing saved
coordinates does not require this extra.

```bash
# Keep exact materials and a lightweight landscape in one compact edition.
hop-design design freeze designs --compact --include-landscape --out compact-edition
```

The Python equivalent is `choices.freeze("compact-edition", compact=True,
include_landscape=True)`. This keeps exact materials in a lossless archive per
preparation and records lightweight molecular descriptors. Opening the map reads
the descriptors; inspecting a point draws its hairpin, and opening the preparation
draws its route. Retrieving materials restores the original files byte for byte.
The original producer and current renderer remain separately identified.

Compact editions check metadata when opened and each authority archive when
accessed. `edition.integrity` reports that distinction. They do not capture the
original artwork: the requested `captured` policy therefore reports `current`
rendering with an explanation. Use ordinary capture when preserving the exact
original SVGs is the priority. Existing editions keep their full opening checks.
Call `edition.verify_integrity()` to check every captured file and archive in a
compact edition. Capture performs this complete byte check before publication;
neither operation repeats molecular compilation.

## Combine independent discovery jobs

For parallel exploration, divide the requested end pairs into disjoint jobs using
the ordinary intent's `ends.left` and `ends.right` alternatives. Keep the same
stem, context, molecular permissions and effort file in every job. Each process
owns one discovery directory and one checkpoint. Worker count and resource
supervision belong to the caller; HOP does not start a background campaign.

After stopping the writers, capture their union against the original full intent:

```bash
# Combine the independent jobs against their original full request.
hop-design design combine job-a job-b --request full-intent.json --out combined-edition
hop-design design query combined-edition --format text
```

`construction.combine_design_discoveries(full_intent, ["job-a", "job-b"],
"combined-edition")` is the same API operation. It requires the jobs' target
grids to cover the declared grid exactly once and rejects changed permissions,
different effort policies or producers. Jobs without preparations still contribute
their coverage. All jobs may be incomplete; complete grid assignment is not
exhaustive molecular search.

The compact edition preserves every captured preparation and exact oligo handoff.
Capture replays those preparations; it does not replay every negative search
result. Its origin record binds each source snapshot and distinguishes that
verification level. Continue searching through the original jobs, then create a
new edition. Never copy or concatenate checkpoint tables. Diversity allocation
is independent within each job, so a fixed compute budget need not discover the
same prefix as one unpartitioned search. Record the partition recipe with the
study's computation costs and coverage.

## Capture a recorded discovery with an updated exporter

To package an existing released-insert discovery after updating HOP, supply an
explicit source contract. This operation reads recorded preparations; it does
not resume the search or authorize execution under a different generator.

```bash
# Bind the original producer when an updated exporter captures old records.
hop-design design freeze designs --compact --source-contract source.json --out recorded-edition
```

The same operation is available as
`construction.freeze_design_choices("designs", "recorded-edition", compact=True,
source_contract="source.json")`. Without `source_contract`, ordinary producer
admission applies. Use `include_landscape=True` or `--include-landscape` to fit
coordinates with the exporter's numerical environment.

`source.json` uses `hop.recorded-design-source/v1`. It binds the original complete
producer identity, the recorded `snapshot_digest`, and a `files` mapping with
SHA-256 digests and byte sizes. Bind `survey.sqlite`, `effort.json`, every file
in `intent/`, and every file in `revision/` when present. Obtain these bindings
from the recorded generator and completed source, before changing environments.
They are input identity checks, not evidence of exhaustive discovery.

Stop writers before capture. HOP rejects SQLite sidecars, changed inputs,
symlinks, mismatched producers and unsupported molecular records. It admits one
read snapshot, verifies every retrieved preparation through the existing
molecular checks, and rechecks source bindings before publishing. Failure
publishes no edition. The returned object is an immutable `AtlasEdition`.

The edition keeps the original producer and binds `capture-origin.json` with
the source contract and current exporter identity. Aggregate discovery replay
remains a separately recorded operation. This import supports exact-stem
released-insert discoveries, compact capture and ordinary parameter filters;
use the original producer for family or preservation-query capture.

## Explore molecules, then their preparations

For proximity-based navigation, capture coordinates once using the
[atlas-enabled installation](install.md#fit-a-new-molecular-map).

```bash
# Capture the molecular landscape for point-by-point inspection.
hop-design design freeze designs --compact --include-landscape --out molecular-edition
hop-design design view molecular-edition --out inspection
```

The map opens with one point per complete preparation. Hover or keyboard-focus
previews its exact hairpin and parameter trace together; clicking or Enter pins
it. Leaving the map or Escape restores the pinned molecule. **Show me another**
samples the eligible pool without changing your requirements. **Fit map** restores
the overview. **Refine choices** reveals parameter filtering and alternate views;
the full route and its processing controls appear after selection.

**Refine → Discover alternatives** starts an explicit, separate discovery branch.
Its request uses the same exact-stem JSON as the API and CLI, initialized with the
atlas's recorded permissions. Set an evaluation budget, then start the search.
The default omits preparation-order references owned by the original discovery.
To reuse one deliberately, add `prefer_preparation` with paths valid from the
launch directory; HOP verifies and captures those files for the new branch.
Progress counts committed evaluations within that invocation, not a percentage
of molecular space. You can keep inspecting the original atlas while it runs.

**Stop** requests a cooperative stop after the current evaluation. Saved work
remains available, and **Continue saved search** appears when continuation is
supported. **Inspect results** explicitly opens a finished, nonempty branch in
this tab. HOP verifies the saved choices and prepares their drawings before
switching; admission failure leaves the original inspector intact. The existing
pin is retained when it belongs to the new pool; otherwise HOP selects a
reproducible example. New results open as structural groups, without fitting UMAP.
The original edition and saved view remain unchanged on disk; reopen them to
return. A public CLI command also opens the saved branch independently.
Search directories stay under the inspection output. Closing the local server
stops and reaps its worker. This control supports exact-stem discovery; use the existing
CLI/API workflows for families or staged revisions.

The map stays in place while the side inspector scrolls. Its first figure pairs
the exact hairpin with the parameter trace; processing scenes load as they enter
view. **Full figure** opens the complete route. **Prepare oligo files** creates
the selected preparation's downloadable materials. Browser and exported teaching
figures share molecular glyphs, with separate layouts for inspector and print
widths. Print exports include a full-resolution route plate and readable
continuation pages; the recorded physical dimensions show the effect of scaling.

Nearby points compare shape, retained scaffold sequence and applicable receiving
ends. The fixed supplied stem and auxiliary primer-handle sequences do not determine
position. Enzyme methods remain visible in the trace. This distance helps find
alternatives; it does not predict activity or establish a controlled comparison.
Under **Preparation details → Nearby alternatives**, HOP describes changed
coordinates. It labels loop surroundings preserved only after its regional
preservation operation verifies that relationship.

Coordinates stay fixed while filtering. Preparations with identical comparison
descriptors share a position. Select that position to inspect its members;
the pinned preparation stays outlined. Static maps preserve those positions and
describe their multiplicity. Alternative preparations do not by themselves
increase molecular diversity.
The saved edition carries its comparison definition, coordinates, algorithm
settings and projector identity. Viewing it needs no numerical dependencies.
Up to 2,048 distinct comparison signatures use exact all-pairs distances. Larger
cohorts use molecular neighbor descent followed by exact molecular reranking.
The saved map records its neighbor audit and minimum recall across examined
queries. Inadequate recall widens retrieval or stops the fit; it never changes
molecular eligibility. This sampled audit is separate from search completeness.
Editions without coordinates open the structural-group view and remain inspectable.

The same inspection operations are available programmatically:

```python
# Draw only the requested preparation preview.
edition.preview(preparation_id).write("hairpin-preview")
edition.neighbors(preparation_id, query=query, limit=5)
edition.figure(selection=selected, view="similarity").write("molecular-figure")
```

```bash
# Inspect one preparation and its materials from the captured edition.
hop-design design preview molecular-edition --preparation ID --out hairpin-preview
hop-design design neighbors molecular-edition --preparation ID
hop-design design figure molecular-edition --selection choice.json \
  --view similarity --out molecular-figure
```

Neighbor ranking compares all eligible preparations using the recorded molecular
distance. Preservation checks then examine only the returned candidates and their
reference. To rank without those additional proofs, use
`edition.neighbors(preparation_id, verify_controls=False)` or
`design neighbors ... --no-verify-controls`. These results report preservation as
unestablished. The inspector uses this faster ranking first; **Check shared
surroundings** requests verification explicitly.

Neighbor calls have a five-second default time budget, adjustable with
`timeout_seconds` in Python or `--timeout-seconds` on the CLI. A stopped operation
reports an error, not an empty solution set. The inspector cancels obsolete work
without holding the lock used for preview and closing. Cancellation takes effect
at computation boundaries; one in-progress molecular verification can finish first.

Previewing does not select, search or change a query. The similarity figure
exports the fixed map in `plot.svg`, and the selected hairpin above its parameter
trace in `figure.svg` and `figure.pdf`,
plus their separate SVGs and the saved coordinates. Exact orders still follow
the selected preparation through `design retrieve`.

The compact `x = […]` strip below the map shows the active descriptor fields in
the saved comparison basis order. Each field connects its molecular value to its
serialized value: counts, ordered contact codes, base lists or end words. Contact
codes identify base pairs and contact classes; their integer differences have no
meaning. Hover or focus a field to highlight the matching molecular span and
parameter axes, or read its encoding and normalization in the tooltip. Constant
features remain inspectable on the molecule and in the edition, but do not occupy
vector fields. The strip changes atomically with the hairpin and trace and retains
the previous view while loading. These are the descriptors underlying the saved
molecular dissimilarity, not UMAP coordinates or an invented Euclidean embedding.
The teaching hairpin shows the matched hairpin-PCR primer pair; source-PCR primers
appear with source ssDNA in the complete route.

New released-insert comparisons use `hop.molecular-comparison/v2`: the two tail
fields describe only hairpin-tail sequence that contributes to the insert.
Recorded copying and primer-binding relationships establish that contribution.
Discarded handle length and sequence do not separate otherwise matching scaffold
choices. Any retained tail bases still contribute through their count and sequence.
The full hairpin, primers and every exact preparation remain available for inspection
and retrieval. Hairpin endpoints retain their complete terminal geometry.

Saved v1 maps keep their original definition, including full hairpin tail lengths.
Opening or filtering an edition does not change its descriptors or coordinates.
Current descriptors require projection from the complete recorded route; a new
comparison cannot be inferred merely by deleting columns from an old map.

### Structural groups and guided sampling

```bash
# Sample across the recorded structural groups with an explicit seed.
hop-design design sample atlas-edition --strategy families --stage hairpin \
  --seed 7 --out choice.json
hop-design design figure atlas-edition --selection choice.json \
  --view families --stage hairpin --out family-figure
hop-design design atlas atlas-edition --selection choice.json --out route
hop-design design retrieve atlas-edition --selection choice.json --out materials
```

The family view groups exact products by recorded structural features. When two
dimensions vary, it uses their measured coordinates. Otherwise it uses a labeled
mosaic whose positions describe grouping rather than distance. Coincident points
retain their complete membership. Multiple preparations of one product do not
increase the product count.

Select a family's enclosure to restrict the complete preparations available;
select a product mark to inspect its preparations. These are separate actions.
Family restrictions intersect the current filters. If the intersection is empty,
the viewer keeps the previous molecule as context and disables retrieval. Clear
the filters or go Back to explore another group.

The same exact restriction is available in Python:

```python
# Read the structural groups through the Python API.
families = edition.families(stage="hairpin")
family_query = families["families"][0]["query"]
matching = edition.query(family_query)
selected = edition.sample(seed=7, query=family_query, strategy="families", stage="hairpin")
```

Save `family_query` as JSON and pass it to `design query --query` or
`design sample --query`. It contains snapshot-bound preparation membership,
not independently inferred axis ranges. An empty membership matches nothing;
unknown preparations and a different snapshot are rejected. Existing queries
without membership retain their meaning and serialized identity.

The small geometry distributions compare eligible with recorded **preparations**.
Their names, molecular stages, units, bins and missing-value counts are also
returned by `families()`; family figure packets include `distributions.svg`.
Several preparations can make the same product, so these counts are not library
diversity. Missing coordinates remain missing, rather than becoming zero.

`--stage hairpin` groups the folded intermediate. `--stage endpoint` groups the
requested final product. The molecule changes with that choice of stage; the
selected preparation remains the same.

Guided sampling first seeks unvisited structural families, then different products,
then preparation alternatives. To continue the same exploration:

```bash
# Apply the additional grouping controls to the recorded pool.
hop-design design sample atlas-edition --strategy families \
  --after choice.json --seed 8 --out next-choice.json
```

The receipt records the query, stage, seed, visited preparations and eligible
membership. It also explains whether the product or only its preparation changed.
The ordinary `design sample --seed 7` retains its original preparation-sampling
behavior. Neither operation starts search or relaxes a requirement.

### Change a loop while keeping its surroundings

Hover or focus the loop in the teaching molecule, then choose **Another loop,
same surroundings**. HOP looks for a different loop word while preserving the
other hairpin regions' sequences, contacts and terminal chemistry. Active filters
remain in force. A fixed loop filter can therefore leave no alternative.

Use the same operation from a saved view:

```bash
# Seek a loop alternative while preserving its verified surroundings.
hop-design design sample atlas-edition --strategy loop \
  --after hop-view.json --seed 8 --out loop-choice.json
hop-design design retrieve atlas-edition --selection loop-choice.json --out materials
```

```python
# Sample the same kind of alternative through Python.
alternative = edition.sample(after=saved_view, strategy="loop", seed=8)
edition.atlas(alternative).write("loop-route")
edition.retrieve(alternative, "loop-materials")
```

The guided receipt retains the incoming query, reference history and exact
selection. The selection's query adds stage-qualified preservation and intersects
the existing eligible preparations. Sampling excludes the reference loop word;
the saved query still permits returning to it on the next step. Empty or singleton
pools report that no different loop is available instead of relaxing a requirement.
This operation samples existing preparations; it does not establish an exhaustive
sequence library or select a required comparative set.

Captured editions reuse the regional comparison rules over their complete route
records. If those records are missing or cannot be read, preservation reports
unsupported scope; ordinary captured viewing and retrieval remain available.
Use `edition.preserve(reference, stage="hairpin", except_neighborhood="loop")`
or `design preserve` to obtain the preservation query without sampling. As with
live choices, that operation starts a new query independently of the locating
filters; the guided loop action explicitly intersects the active filters.

Client adapters can validate view settings with
`choices.inspection_settings(presentation=..., exploration=...)` before selecting
a preparation. `choices.plot_svg_bytes(view="distributions", stage="hairpin")`
renders the contextual geometry from the same family projection.
`choices.atlas(selection).inspection_summary(selection)` returns compact navigation
facts; the packet retains its complete molecular record. Browser adapters use
these public objects instead of importing internal models or renderers.

## Use the same objects from Python

```python
# Open and query the frozen edition through Python.
from hop_design import construction

choices = construction.load_design_choices("designs")
edition = choices.freeze("atlas-edition")
selected = edition.sample(seed=7, strategy="families", stage="hairpin")
edition.figure(selection=selected, view="families", stage="hairpin").write("family-figure")
edition.atlas(selected).write("route")
edition.retrieve(selected, "materials")

view = edition.view(selected, stage="all")
relocated = construction.load_atlas_edition("copied-atlas-edition")
relocated.restore_view(view)
```

The original producer is recorded in `edition.json`; newly rendered figure packets
identify their display renderer separately. Loading checks file inventory and
digests. Selection checks membership and query eligibility; guided receipts replay
their sampling inputs. Captured evidence remains captured evidence, rather than a
claim of molecular revalidation by the current installation.

Use the original discovery for new evaluations or revised construction permissions.
The frozen edition is a reusable viewing and retrieval surface.

## Inspect without changing the request

```bash
# Open the saved edition without starting new discovery.
hop-design design view atlas-edition --out inspection
hop-design design parameters atlas-edition
```

The same local viewer opens live hairpin choices, insert choices and frozen editions.
**Show me another** samples a complete eligible preparation. **Structural groups**
changes the landscape view; **Full preparation** focuses the route. Neither action
changes the request. Filtering to an empty set leaves the last molecule visible
as outside the query, with retrieval disabled. Clear the filters to recover it.

The inspector opens with a compact shape/interface trace: basal
paired extent, both end words and gaps, loop-side extension and loop size, where
applicable. Fixed values stay visible. The full parameter data and query remain
available; this drawing choice does not restrict the preparations in the map.

**Download view** records the query, exact preparation, reference, inspected stage,
camera, landscape and molecular modes, family grouping stage, drawing policy,
ordered display axes when specified, the color property and highlighted word,
and next sampling seed/history.
**Open saved view** restores that receipt against
the same edition. A local
link includes the receipt in its fragment; share the edition directory as well.
The receipt does not start a server or make the edition publicly available.

Captured artwork remains the default, including during comparison. Under
**Reproduce & inspect**, choose **Current glyphs · compact assembly** to use the
shared assembly composition, or **Current glyphs · all states** to display every
recorded state. If the schema
cannot be interpreted, HOP retains the captured drawing and reports the effective
policy. It does not migrate molecular authority.

The same choice belongs to the saved inspection:

```python
# Save a view tied to the current preparation and query.
view = edition.view(
    selected,
    render_policy="current",
    presentation={"molecule": "route", "route": "assembly"},
)
edition.atlas(view).write("assembly-route")
```

Assembly combines cleanup into one transition and retains the annealed scene.
For the eleven-state example this displays nine scenes; no molecular state is
removed from the record. Choosing an omitted cleanup state exposes it in the
complete route. Returning to **All processing steps** restores assembly. The
rendering receipt reports requested/effective composition and displayed/recorded
state counts. Requesting assembly with captured rendering leaves the original
artwork unchanged and explains how to obtain a current redraw. Older v2 views
without `presentation.route` retain `complete` as their default.

Pass the saved view to `atlas()`, `figure()` and `retrieve()`, or use it as the CLI
selection file. `design view --receipt view.json` restores inspection;
`design sample --after view.json` resumes the recorded sampling state. An explicit
figure query must agree with its selection. Rendering policy and camera state
never change molecular identity or oligo orders. V1 views load with documented
default presentation and sampling fields. Parameter and family views use
`hop.atlas-view/v2`; similarity views use `hop.atlas-view/v3` and additionally bind
the saved coordinate digest. Views with explicit `presentation.display_axes`
use `hop.atlas-view/v4`; similarity views still bind the coordinate digest.
The ordered canonical keys govern the linked inspector trace and exported
parameter figure. An explicit `figure(display_axes=...)` overrides that recipe
in the returned figure's view receipt. Unsupported or repeated axes are rejected.
A mismatched map is rejected rather than refitted.

Color views use `hop.atlas-view/v5`. They retain the same selection and optional
axis recipe, with an explicit numeric property, exact sequence word, or no grouping:

```python
# Keep the alternative presentation in its own saved view.
view = edition.view(
    selected,
    presentation={
        "landscape": "similarity",
        "color": {"key": "left_end_word", "word": "AGTC"},
    },
)
edition.figure(selection=view).write("colored-landscape")
```

Use a word recorded in the edition. Numeric keys are `left_gap`, `right_gap`,
`loop_nt` and `foldback_arm_bp`; sequence keys are `loop_word`, `left_end_word`
and `right_end_word`. `{"key": "none"}` records no grouping. Labels, units and
stage meanings come from the molecular parameter catalog. Numeric scales use
the full recorded pool, so filtering does not move colors or coordinates.
The browser repaints color locally; **Download view** validates and records it through
the same API. `design figure --selection view.json` reproduces the colored map.
Unknown properties, absent words and inapplicable coordinates are rejected.
Older receipts remain readable and do not claim to contain a saved color choice.

Full-route previews retain at most four packets and 128 MiB of files; plot artifacts
use a separate four-entry, 16-MiB cache. The browser loads the visible molecular
view and keeps a six-entry, 8-MiB artifact cache. Closing the server removes its
temporary previews and plots. Lightweight teaching previews and visible route
scenes each retain up to 12 entries within one shared 8-MiB file budget. They
never generate the complete route or a PDF.
Requested material downloads remain in
the inspection output directory. Multipage print figures are generated on export,
not on every selection.

## Specify and compare molecular distances

The [molecular comparison contract](../reference/molecular-comparison.md) defines
feature types, exact formulas, versioned optional policies and the shared
`freeze` API/CLI. New policies create separate editions; they do not replace
saved atlas coordinates.
