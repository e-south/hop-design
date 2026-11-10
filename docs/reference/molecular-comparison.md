# Molecular comparison

A molecular comparison assigns a dissimilarity to recorded preparations using
their geometry, regional sequences and receiving ends. Smaller distances mean
closer agreement under the saved comparison policy. The supplied stem and
endpoint define which preparations are being compared.

| Feature type | Contents | Comparison |
| --- | --- | --- |
| Geometry | Stage-qualified counts: loop nt, added paired bp, basal contact positions, tails and applicable insert gaps | Absolute difference divided by a saved scale |
| Regional sequence | Ordered loop bases and oriented `(base, paired base, contact class)` tokens; applicable retained tail bases | The declared sequence dissimilarity |
| Receiving interface | Exact words on their protruding strands and recorded polarity | Declared word dissimilarity; nominal polarity mismatch |

The **descriptor** is the record of molecular features used in this comparison;
a **coordinate** is one measured count or encoded sequence/contact feature in
that record. The complete descriptor remains available even when a coordinate
is constant.
Only varying coordinates contribute to distance. An integer representing a
contact identifies its category without losing information: subtracting two
codes has no molecular meaning. Geometry and sequence regions have explicit
boundaries in the molecular projection.

## Saved policy

`MolecularComparisonBasis` records scales, active fields, three block weights and
the compared signatures. Its optional `distance_policy` has schema
`hop.molecular-distance/v1`:

| Field | Values | Meaning |
| --- | --- | --- |
| `regional_metric` | `length_adjusted_edit`, `normalized_edit` | Original residual sequence penalty, or edit count divided by the longer region |
| `end_word_metric` | `normalized_edit`, `hamming` | Shift-permitting edit count, or fixed-register mismatch fraction |
| `numeric_scaling` | `observed_range`, `declared` | Edition range, or caller-declared coordinate scales |
| `declared_scales` | Coordinate-to-positive-count mapping | Required for each varying geometry field when scaling is declared |
| `constant_features` | `omit` | Constant coordinates have no weight |
| `contact_tokens` | `oriented_base_pair_and_class` | One whole contact is one nominal token |

For region lengths `m,n` and edit count `e`, the original sequence penalty is
`min(1, max(0, e − abs(m−n)) / max(1,min(m,n)))`. Its length correction can assign
zero sequence penalty to insertions. Ordinary normalized edit uses
`e / max(1,m,n)`.

Hamming requires equal word lengths within each side of the cohort. Words retain
their recorded orientation; reverse complements are not silently equated.
Declared scales must cover the observed ranges. Invalid scales or unequal
Hamming lengths raise, rather than clipping or changing metric.

Distances are averaged within each active block, then combined as
`sum(weight × block_mean) / sum(active_weights)`. Default weights are `1,1,1`.
Thus a block with many coordinates does not automatically dominate another
block. The caller declares weights, scales, molecular controls and sensitivity
criteria for the comparison.

Legacy records omit `distance_policy`; omission retains the original arithmetic
and serialization. Descriptor schemas are a separate dimension:
`hop.molecular-comparison/v1` includes complete hairpin tail lengths;
`v2` compares retained tail contributions for released inserts. Changing a metric
does not automatically change that descriptor scope or any preparation identity.

## Capture an explicit comparison

```python
# Declare how molecular descriptors contribute to dissimilarity.
from hop_design.models.construction.variants.similarity import MolecularDistancePolicy

policy = MolecularDistancePolicy(
    regional_metric="normalized_edit",
    end_word_metric="hamming",
)
edition = choices.freeze(
    "candidate-edition",
    include_landscape=True,
    distance_policy=policy,
    comparison_weights=(1, 1, 1),
)
```

The same policy JSON is accepted by the existing CLI:

```bash
# Capture the edition with its explicit molecular comparison definition.
hop-design design freeze designs --include-landscape \
  --distance-policy distance.json --comparison-weights 1 1 1 \
  --out candidate-edition
```

Capture is create-only. An explicit comparison requires `include_landscape=True`.
Existing editions remain unchanged. The browser's descriptor explanations read
the captured policy; hover and filtering do not fit coordinates or revise scales.
Selections, routes and retrieved materials retain their exact identities.
An existing `choices.figure(view="similarity", selection=selection)` export also
contains `comparison-features.json` and `comparison-features.svg`. They describe
that selected point using the same contact dictionary, active coordinate order
and policy as the browser. The JSON retains constant features and the dictionary;
the SVG draws a literal `X = [ … ]` row in captured feature order. It shows
geometry with units, oriented words, and decoded contact rows with canonical
lines and noncanonical diamonds. These values retain their scientific types;
the displayed row is not a Euclidean embedding. Exact encodings remain in
per-feature attributes and the embedded record; nominal IDs imply no numerical
ordering. The browser uses the same horizontal reading within the map pane.

For a column-width selected detail, request the physical width explicitly:

```python
packet = edition.figure(
    selection=selected,
    view="similarity",
    display_axes=existing_axes,
    render_policy="current",
    detail_width_pt=246,
)
```

`trace.svg` keeps every declared axis in one row, with horizontal category values
and measured, context-shortened headings. Complete canonical labels remain in node
titles and metadata. The column profile retains at least 7 pt type or reports the
minimum required width; it never silently drops axes or reduces labels below that
budget. `comparison-features.svg` retains a natural-width single row independently of
the trace width, with 7.2 pt labels, 9 pt scalar/word values and 8.5 pt contacts.
A longer record expands rather than dropping features or splitting tokens. The selected map, exact comparison JSON, materials and view identity
are unchanged. The figure summary records the explicit width and presentation
profile independently of the saved scientific view. The browser uses the same compact contextual headings in a fitted plate of at
most seven inches; narrowing the inspector does not enlarge its molecule.
Complete trace context remains embedded metadata without a visible status footer.

Parallel connections use cubic curves with shared mid-transition control points
for identical adjacent endpoints. This is a presentation aid for following shared
transitions, not a hierarchy, clustering analysis or new distance. Every path keeps
its exact preparation membership and the same axis endpoints; SVG hit paths and
inspection overlays use that same geometry.

Recapturing an edition inherits its comparison policy and weights unless explicitly
replaced. An unchanged complete descriptor set reuses its saved landscape.
Its recorded descriptor scope is also preserved and checked against retrieved
materials; compact storage conversion does not switch full-tail to retained-tail
comparison.

For methodological context, the numeric and nominal terms follow the general
mixed-dissimilarity approach described by
[Gower implementations](https://stat.ethz.ch/R-manual/R-devel/library/cluster/html/daisy.html).
The regional sequence terms make this a custom block-weighted comparison, not
canonical Gower. UMAP receives the resulting distances or audited neighbor graph;
the displayed descriptor is not treated as a Euclidean vector.
