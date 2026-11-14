# Navigate a collection by molecular similarity

Capture a saved [discovery](../discover-designs.md) as a collection with fixed
map coordinates, then inspect its preparations and their exact materials.
The capture commands below need a new output directory.

For the Python operations, import `construction` as in the
[capture example](../share-atlas-edition.md#use-the-same-objects-from-python) and
load `edition` with `construction.load_atlas_edition("molecular-edition")`.
Set `query` to the eligibility filter (`{}` includes every member), retain the
selection returned by `edition.sample(seed=7, query=query)` as `selected`, and
set `preparation_id = selected["materialized_realization_id"]`. These objects
must refer to the same edition.

## Explore molecules, then their preparations

For proximity-based navigation, capture coordinates once using the
[optional map dependencies](../install.md#fit-a-new-molecular-map).

```bash
# Capture the molecular landscape for point-by-point inspection.
hop-design design freeze designs --compact --include-landscape --out molecular-edition
hop-design design view molecular-edition --out inspection
```

The map opens with one point per complete preparation. Hover or keyboard-focus
previews its exact hairpin and parameter trace together; clicking or Enter pins
it. Leaving the map or Escape restores the pinned molecule. **Show me another**
samples the eligible pool without changing your requirements. **Fit atlas** restores
the overview. **Atlas options → Other population views** reveals structural groups
and population parameter traces;
the full route and its processing controls appear after selection.

**Atlas options → Discover alternatives** starts an explicit, separate discovery branch.
Its request uses the same exact-stem JSON as the API and CLI, initialized with the
collection's recorded permissions. Set an evaluation budget, then start the search.
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

Below the preparation, **Choice frequencies** counts recorded preparations using
each parameter value or oligo material. Choose a component, hover a bar to
highlight its preparations in the map and parameter traces, or click to keep
that highlight. **Clear highlight** or Escape removes it. These highlights do
not change filters or select a preparation. The last bar groups choices outside
the twelve most frequent; its highlight includes every preparation in that group.
Counts include recorded preparations outside the current filters, with the
eligible count shown separately.

The molecular map arranges recorded preparations for navigation. Read the saved
search coverage separately from map distances, clusters and point density.

Nearby points compare shape, retained scaffold sequence and applicable receiving
ends. The fixed supplied stem and auxiliary primer-handle sequences do not determine
position. Enzyme methods remain visible in the trace.
Click a labeled molecular feature and choose **Meaning** to read its measurement
and molecular stage. **Atlas options → Save view** downloads the current inspection;
**Open saved view** restores it. **Download molecular record (.json)** provides the
selected preparation's record. Detailed comparisons,
costs, correspondence diagnostics and reproduction commands remain available in
records, exports and the API/CLI; they are not repeated below the drawings.
Rendering and route-composition policies remain explicit API/CLI options.

Coordinates stay fixed while filtering. Preparations with identical comparison
descriptors share a position. Select that position to inspect its members;
the pinned preparation stays outlined. Static maps preserve those positions and
describe their multiplicity. Count products separately from their alternative
preparations.
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
unestablished. Use `verify_controls=True` or omit `--no-verify-controls` to request
the preservation checks.

Neighbor calls have a five-second default time budget, adjustable with
`timeout_seconds` in Python or `--timeout-seconds` on the CLI. A stopped operation
reports an error, not an empty solution set. Cancellation takes effect at
computation boundaries; one in-progress molecular verification can finish first.

Previewing does not select, search or change a query. The similarity figure
exports the fixed map in `plot.svg`, the selected hairpin above its parameter
trace in `figure.svg` and `figure.pdf`, separate SVGs, and the saved coordinates.
Exact orders follow the selected preparation through `design retrieve`.

The compact `X = […]` strip below the map shows the active fields in the saved
comparison order. Geometry entries are measurements. Other entries are per-field
lookup codes for exact contact sequences, bases or end words. Code 74 does not mean
74 contacts, and subtracting two codes does not give a molecular distance. The
[comparison reference](../../reference/molecular-comparison.md) defines how the
decoded values are compared.

**How X is read**, at the lower left of the atlas, explains the selected field's
value and comparison rule. Click or keyboard-activate a field to open its
explanation. Hover or focus highlights the corresponding molecular region and
parameter axes. The strip and explanation update together with the hairpin and
trace. Constant fields remain in the molecular record but do not occupy the strip.
Viewing or filtering never refits the saved comparison or coordinates.

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

## Specify and compare molecular distances

The [molecular comparison contract](../../reference/molecular-comparison.md) defines
feature types, exact formulas, versioned optional policies and the shared
`freeze` API/CLI. New policies create separate editions; they do not replace
saved atlas coordinates.

For sampling history, controlled loop changes and reproducible drawing settings,
use [structural sampling and saved views](sampling-and-saved-views.md).
