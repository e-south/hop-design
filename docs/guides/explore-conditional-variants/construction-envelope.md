# Explore the construction envelope

Inspect the permitted parameter domains, evaluate selected possibilities and
revise generating permissions explicitly. Use a [source checkout](../install.md#work-from-source)
and its locked environment. The example below creates its own `/tmp/hop-envelope`
result; it is separate from the [conditional comparison example](../explore-conditional-variants.md).
Use new output directories throughout. For Python inspection, import
`construction` from `hop_design` and load `pool` with
`construction.load_scaffold_exploration("/tmp/hop-envelope")` after discovery.

The **construction envelope** is the set of molecular choices permitted by the
request. The parallel-coordinate plot shows those choices on separate axes;
each path connects the parameter values for one recorded preparation. It keeps
the evaluated network visible while you narrow it. Solid paths represent
complete preparations; faint paths preserve excluded context. Dashed segments
represent verified **local** foldback or basal
realizations. They stop before unassessed axes and cannot be selected as complete
products. Choose a recorded complete path to preserve compatible surroundings;
crossing paths cannot be recombined.

Run the broader, bounded [construction-envelope request](../../../examples/molecular-editing/construction-envelope.json):

```bash
# Discover scaffolds under the explicit construction envelope.
uv run --locked hop-design construction discover-scaffolds examples/molecular-editing/construction-envelope.json --out /tmp/hop-envelope
uv run --locked hop-design construction edit-view /tmp/hop-envelope --evaluated --out /tmp/hop-envelope-view
```

This public synthetic request fixes the receiving end words, permits paired
placements 6/6 and 0/0 bp and two basal nickases. Foldback arm and loop lengths
are free within a 32-nt retained-construction budget, with declared minima of 3 bp
and 3 nt. Join displacements span 0–16 nt; geometry and enzyme constraints still
exclude incompatible combinations. No loop-word shortlist is supplied. Four method/placement
branches each allow up to 40 local realizations and 40 continuations. These are
computation limits, not molecular restrictions. Early compact local candidates may
fail the retained 14-nt source-primer requirement. Those failures remain visible.
Remaining permissions stay visible even when no complete path reaches them.

## One vocabulary for the diagram, axes and query

Select a molecular feature to inspect its quantities, then expose the related
coordinates in the plot. Hover or keyboard-focus an axis to locate the quantity
and its dependencies in the teaching key and throughout the atlas. Parameter definitions
include symbol, units, molecular stage, measurement boundaries and dependencies.
See the [parameter and teaching-glyph coverage specification](../../reference/molecular-parameters.md)
for the three coordinate frames and explicit nonspatial context.
For example, **A** is the total added paired arm in base pairs, **D** is the nick
displacement in nucleotides, and the post-nick self-paired arm is **R = A − D**
base pairs. Selecting a range on the R axis (brushing) filters compatible A/D
pairs; it never makes R independently editable.

Each axis distinguishes its declared domain from the observed values. **Fixed by
request** means the request permits one value; **constant among evaluated results**
means the recorded preparations happen to agree. A requirement is not an achieved
measurement. In particular, required adapter annealing is a threshold; achieved
annealing counts the full recorded source/adapter association, not just the local
basal contact window.

The primer-boundary view connects a rejected continuation to its examined source:
the pale stem fill is retained, the available outside-stem flank has its own
bracket, and the required primer footprint shows why that continuation fails.
The diagram shows the examined source. Buttons beneath it inspect complete
alternatives from the same branch that satisfy the current selections.
Portable choice exports include `primer-boundaries.svg` and all individual
failure records in `choice_space.primer_boundaries`. The atlas separately locates
required primer footprints and available flanks on a complete preparation.
Zero-length measurements retain coincident boundary markers.

Dense domains prioritize selected and supported labels. Focus an axis or choose
**Browse…** to inspect its full domain. Resizing changes presentation only.

The default order connects foldback geometry, basal method and displacement,
released-end gaps and the source-primer span. Method and receiving-interface
permissions remain visible beside the plot, including fixed words and polarities.
Selecting an ordered source/adapter contact exposes its source base, adapter base
and contact class together. Positions count outward from ligation, beginning at
zero.

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

## Evaluate a selected region explicitly

**Coverage and further bounded evaluation** distinguishes declared branch domains,
examined continuations and local exclusions from unexamined branches. Failed
continuations do not receive invented downstream coordinates. Achieved contact
counts and terminal dimensions can remain unassessed until a complete route exists.

Brushing only filters existing evidence. **Evaluate selected region** runs a new,
explicitly bounded evaluation under the active generating permissions intersected with the
selected parameters. Numeric and positional constraints narrow their owning local
generator where supported; remaining achieved-property controls are checked after
construction. Required panel targets outside the selected region stay recorded as
outside this evaluation round. Its packet retains the previous pool unchanged.
The union preserves original labels, deduplicates exact preparations and reapplies
the query; coverage counts evaluation records, which can overlap across rounds.

The equivalent file-oriented operation is:

```text
uv run --locked hop-design construction variants RESULT --query QUERY.json --out CHOICES
uv run --locked hop-design construction evaluate-parameters RESULT CHOICES --max-branches 4 --max-continuations 1 --out EXTENDED
```

The query needs the current `result_digest`, ordinary stage/focus fields and, for
example, `"parameters": [{"key": "self_paired_arm_bp", "minimum": 7, "maximum": 8}]`.
Reload `EXTENDED` and reissue the query with its new result digest. CLI/API use the
same immutable evidence as the browser. To expand a generating permission, use
the separate revision operation below.

## Browse unobserved values and revise the envelope

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
Preview checks the declarations; evaluate the revised request to check completion.

For example, keep a selected R = 9 while changing an arm domain from 8–10 to 10–12
bp. The old domain supplies only A/D = 10/1; the revised domain can also test 11/2
and 12/3 when those D values are permitted. Arithmetic compatibility does not imply
molecular completion. This is an explicit revision, not a hidden relaxation.

```text
uv run --locked hop-design construction parameter-values RESULT CHOICES --parameter loop_word --length 4 --prefix AA --out VALUES
uv run --locked hop-design construction revise-envelope RESULT CHOICES REVISION.json --out PREVIEW
uv run --locked hop-design construction evaluate-envelope RESULT PREVIEW --max-branches 4 --max-continuations 4 --out EXTENDED
```

The executable [envelope example](../../../examples/molecular-editing/envelope.py)
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
lists the filtered choices. Previously saved choices must be
regenerated against their original pool after a projection change; never edit or
reseal historical packets.

For local route inspection and required comparative sets, return to
[conditional exploration](../explore-conditional-variants.md). Export and inspect
the resulting query through the [CLI and Python workflow](cli-and-python.md).
