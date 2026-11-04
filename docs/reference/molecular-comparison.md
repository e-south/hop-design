---
doc_id: hop-molecular-comparison
title: Molecular comparison
intent: Explain typed molecular descriptors, versioned distances and frozen atlas comparisons.
audience:
  - API consumers
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-10-28
doc_type: reference
---

# Molecular comparison

A comparison describes proximity between recorded preparations. It does not
admit a new construction, prove compatibility or predict biological activity.
The supplied stem and endpoint define the comparison scope.

| Feature type | Contents | Comparison |
| --- | --- | --- |
| Geometry | Stage-qualified counts: loop nt, added paired bp, basal contact positions, tails and applicable insert gaps | Absolute difference divided by a saved scale |
| Regional sequence | Ordered loop bases and oriented `(base, paired base, contact class)` tokens; applicable retained tail bases | The declared sequence dissimilarity |
| Receiving interface | Exact words on their protruding strands and recorded polarity | Declared word dissimilarity; nominal polarity mismatch |

The complete descriptor remains available even when a coordinate is constant.
Only varying coordinates contribute to distance. A contact integer is a lossless
category code: subtracting two codes has no molecular meaning. Geometry and
sequence regions have explicit boundaries in the molecular projection; their
names do not denote universal RNA folding classes.

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
`e / max(1,m,n)`. Neither is a learned substitution or energy model.

Hamming requires equal word lengths within each side of the cohort. Words retain
their recorded orientation; reverse complements are not silently equated.
Declared scales must cover the observed ranges. Invalid scales or unequal
Hamming lengths raise, rather than clipping or changing metric.

Distances are averaged within each active block, then combined as
`sum(weight × block_mean) / sum(active_weights)`. Default weights are `1,1,1`.
Thus a block with many coordinates does not automatically dominate another
block. Weights and scales express a declared comparison, not biological truth.
Application-specific molecular controls and sensitivity criteria belong to the
caller, outside HOP.

Legacy records omit `distance_policy`; omission retains the original arithmetic
and serialization. Descriptor schemas are a separate dimension:
`hop.molecular-comparison/v1` includes complete hairpin tail lengths;
`v2` compares retained tail contributions for released inserts. Changing a metric
does not automatically change that descriptor scope or any preparation identity.

## Capture an explicit comparison

```python
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
hop-design design freeze designs --include-landscape \
  --distance-policy distance.json --comparison-weights 1 1 1 \
  --out candidate-edition
```

Capture is create-only. An explicit comparison requires `include_landscape=True`.
Existing editions remain unchanged. The browser's descriptor explanations read
the captured policy; hover and filtering do not fit coordinates or revise scales.
Exact selection, routes and material retrieval retain their existing authority.
An existing `choices.figure(view="similarity", selection=selection)` export also
contains `comparison-features.json` and `comparison-features.svg`. They describe
that selected point using the same contact dictionary, active coordinate order
and policy as the browser. The JSON retains constant features and the dictionary;
the SVG draws the active `x` without wrapping or abbreviating encoded values.
Its natural width follows its contents. A publication composer must check the
final type size rather than shrink a long vector into an unreadable label.
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
