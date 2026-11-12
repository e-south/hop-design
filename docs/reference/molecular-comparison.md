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
the SVG draws a single numeric `X = [ … ]` row in captured feature order.
Geometry keeps physical measurements and units. Each other number identifies
one exact value in its field's cohort-wide dictionary. Dictionaries are ordered
independently of member order, so hover, filtering and browser/export ordering
cannot renumber a code within the same cohort. A different cohort can have a
different dictionary. Codes have no numerical distance or ranking meaning.

The row groups geometry, sequence and ends using shared presentation metadata.
Regular-weight labels descend at 45 degrees. Exact oriented words, contacts,
pairing classes and encodings remain in the JSON, SVG metadata and browser field
explanations; the molecular inspector retains nucleotide resolution. The saved
comparison policy, rather than Euclidean distance between these display codes,
determines map proximity. An older saved comparison is never expanded merely to
match the number of fields in another figure.

In the browser, **How X is read** opens a local explanation beside the atlas.
Choose a field there, or activate its value in X, to see the current measurement
or dictionary code, its decoded molecular value and the saved comparison rule.
The explanation follows the same committed preparation as X and the inspector.
For example, a basal-contact code of 74 identifies one exact ordered pattern;
it does not mean 74 contacts. The pattern length and oriented contacts are shown
after decoding. This display code is also distinct from the numerical kernel's
internal token identifiers. No one-hot feature matrix or Euclidean code distance
is implied. Changing that representation requires a separately qualified fit.

The linked inspector uses the same molecular and parameter renderers as export.
Its side-panel behavior and hover/pin lifecycle are independent of typography.
The hairpin and trace keep a common fitted width; sparse alternative values use
quieter versions of the same value cells. All declared support states and exact
transition membership remain available.

A saved color lens may use `{"key": "max_end_gap"}` to color the larger of the
left and right end gaps, in bp. It requires both measurements; a missing side
remains missing rather than becoming zero. The lens changes display color only,
never a query, comparison field, coordinate, or preparation identity.

To export a column-width hairpin and parameter trace without fitting a map:

```python
preview = edition.preview(preparation_id, detail_width_pt=246)
preview.write("selected-detail")
```

This works with live choices and captured or compact editions, including editions
without a saved landscape. Both SVGs use the existing column-detail profile;
all declared axes, exact bases and selection identity remain intact. An explicit
width uses current molecular rendering and records the width and profile in the
packet summary. Unsupported current projections fail instead of silently returning
captured artwork at a different size. Omitting the width preserves the existing
preview and browser behavior.

For a selected detail alongside a saved similarity map, request the physical width explicitly:

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
budget. `comparison-features.svg` keeps a single numeric row within the requested detail
width, with 7.2 pt angled labels and 9 pt values. Non-numeric values have
field-specific dictionary codes, with their exact meanings embedded. The selected map, exact comparison JSON, materials and view identity
are unchanged. The figure summary records the explicit width and presentation
profile independently of the saved scientific view. The browser uses the same compact contextual headings in a fitted plate of at
most seven inches; narrowing the inspector does not enlarge its molecule.
Observed complete routes appear as quiet curves behind the selected route.
Sparse context values use the same cell shape as selected values; dense values
remain unlabeled rather than becoming a second visual grammar. Complete trace
context also remains embedded metadata without a visible status footer.

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


Presentation maintenance stays separate from molecular rules. Role inks and the
ordered population ramp belong to `export/construction/presentation/palette.py`;
the browser ramp has an explicit parity test against that owner. Group spans
come from `presentation/comparison.py`, physical budgets from `figure_profile.py`,
and site visibility from `molecular/primitives/annotation_policy.py`. A later
palette change should update this presentation layer, not molecular identities,
sequence neighborhoods, search rules or manuscript-specific layout code.

The molecular preset is the immutable `MOLECULAR_PALETTE` record, currently
`compass-pastel`. Its three opaque six-digit hex fills determine basal, stem and
foldback/loop colors; malformed colors fail before drawing. Recognition ink and
pale region headings derive from those fills. Small nucleotide text uses white
when its fill provides at least 4.5:1 contrast, and black otherwise. Population
ramps and `POPULATION_ACCENT` have their own meaning and do not change when a
molecular fill changes. Color-vision simulations are review aids, not palettes
or molecular transformations. Current rendering redraws saved facts with these
tokens; captured rendering intentionally retains the original artwork.

Processing views show recognition footprints before cleavage, quiet spent sites
through retention and folding, and introduce release sites with the adapter.
The released insert retains site metadata without painting residual nickase
fragments. Structural teaching views retain the contextual footprints needed to
locate features. Both views keep every recognition record and address. Stage
titles clear nearby content; distant raised handles do not force a blank title
row. Column turns and the copying connector use rounded horizontal/vertical
segments. Bent primer tips receive bounded local clearance before the whole
binding span moves away from its template.

The parameter-region strip is an explicit `FigureProfile.region_strip` setting:
publication profiles keep it above the axes; the inspector places it below the
angled labels. Unsupported placements fail before drawing. The same measured
axis frame supplies SVG exports and live inspection links; this setting changes
neither the parameter values nor selection behavior.
