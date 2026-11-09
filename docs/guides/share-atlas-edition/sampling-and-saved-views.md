# Sample a collection and save the view

Start with a [captured collection](../share-atlas-edition.md). CLI examples use
`atlas-edition`; the [Python capture example](../share-atlas-edition.md#use-the-same-objects-from-python)
defines `edition` and an explicit `selected` preparation. Keep both objects
for the Python snippets below, and use new paths for exported files.

For loop sampling, `saved_view` is a receipt returned by `edition.view(selected)`.
The CLI example uses a receipt downloaded as `hop-view.json` from that edition.
[Open the viewer](../share-atlas-edition.md#inspect-without-changing-the-request)
to download or restore the same receipt.

## Structural groups and guided sampling

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
Several preparations can make the same product; use the product groups for
unique-product counts. Missing coordinates remain missing rather than becoming zero.

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

## Change a loop while keeping its surroundings

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
This operation samples existing preparations. To require a comparative set, use
the [comparison workflow](../specify-a-comparison.md).

Captured editions reuse the regional comparison rules over their complete route
records. If those records are missing or cannot be read, preservation reports
unsupported scope; ordinary captured viewing and retrieval remain available.
Use `edition.preserve(reference, stage="hairpin", except_neighborhood="loop")`
or `design preserve` to obtain the preservation query without sampling. As with
live choices, that operation starts a new query independently of the locating
filters; the guided loop action explicitly intersects the active filters.

For the adapter recipes below, use `choices = edition` and
`selection = selected` from the same collection.

Client adapters can validate view settings with
`choices.inspection_settings(presentation=..., exploration=...)` before selecting
a preparation. `choices.plot_svg_bytes(view="distributions", stage="hairpin")`
renders the contextual geometry from the same family projection.
`choices.atlas(selection).inspection_summary(selection)` returns compact navigation
facts; the packet retains its complete molecular record. Browser adapters use
these public objects instead of importing internal models or renderers.

## Save drawing and color settings

Captured artwork remains the default, including during comparison. Under
**Reproduce & inspect**, choose **Current glyphs · compact assembly** to use the
shared assembly composition, or **Current glyphs · all states** to display every
recorded state. If the schema
cannot be interpreted, HOP retains the captured drawing and reports the effective
policy, preserving the captured molecular records.

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

The similarity example requires [saved map coordinates](molecular-map.md). Load
that collection as `edition` and sample `selected` from it before running the block.

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
Older receipts remain readable without a saved color choice.

Route previews load on demand. Material downloads remain in the inspection output
directory, and multipage print figures are generated on export. Closing the server
removes temporary previews and plots.

Return to [capture and opening](../share-atlas-edition.md), or inspect
[molecular-map distances and neighbors](molecular-map.md).
