# Share a preparation collection

A preparation collection (an `AtlasEdition` in the API) saves complete
preparations, exact materials and producer identity from a discovery. Each
preparation specifies input oligos and an ordered route to its product; several
preparations may make the same exact molecule. The **producer** is the HOP build
and Python environment that generated and checked those records. Keep the
original drawings or draw selected molecules on demand. Move the directory to
share and inspect it without rerunning the search.

A discovery retains evaluated search work; a collection saves fixed preparation
membership. An optional molecular map positions the collection for navigation.
The `design atlas` command exports one selected processing route.

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

Ordinary capture uses the original compatible producer to verify and read the
discovery. Once captured,
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

Compact editions check metadata when opened and each preparation archive when
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
owns one discovery directory and one checkpoint. Set and supervise the worker
count yourself.

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

After updating HOP, capture existing records with an explicit source contract.
See [recorded capture](../reference/external-artifacts.md#capture-a-recorded-discovery-with-an-updated-exporter)
for the command, required bindings and supported scope. This exports recorded
preparations; it does not resume their search under a different producer.

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
their sampling inputs. The current installation checks captured files and
selections; the edition retains the original producer's molecular verification.

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
the same edition. A local link includes the receipt in its fragment; share the
edition directory as well.

## Explore and save an inspection

Use the [molecular map](share-atlas-edition/molecular-map.md) to inspect nearby
preparations, read the saved distance definition, or start an explicit discovery
branch from the collection.

Use [structural sampling and saved views](share-atlas-edition/sampling-and-saved-views.md)
to sample different products, change a loop with verified surroundings, or save
drawing and color settings. These inspection choices retain the exact
preparation and material identities.
