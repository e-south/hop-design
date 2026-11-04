---
doc_id: hop-guide-survey-interfaces
title: Keep your stem and obtain requested sticky ends
intent: Find complete constructions for a supplied stem and desired ends, inspect their molecular routes, and retrieve exact oligos.
audience: [users, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-11
doc_type: how-to
journey: [discover, verify, integrate]
---

# Keep your stem and obtain requested sticky ends

> Preserve my supplied stem and produce left AGTC / right AACC. Which permitted
> geometries, sequences and methods can accomplish that, and what additional DNA
> would each construction retain?

Start with that molecular request. HOP searches the permitted basal and foldback
choices for complete preparations. Select a matching path to see the entire
processing route and retrieve its source, adapter and primers. The requested
sticky ends belong to the released duplex insert.

## 1. State your stem, ends and permissions

After [installing HOP](install.md), copy the
[complete survey request](../../examples/complete-construction/interface-survey.json).
From a source checkout:

```bash
cp examples/complete-construction/interface-survey.json survey.json
```

Edit these fields before starting:

| Your requirement | Request field |
| --- | --- |
| Stem to preserve | `stem_arm`: one exact DNA arm; HOP derives its partner |
| Desired sticky ends | `targets.left_words`, `targets.right_words` |
| End direction and polarity | `interfaces.left`, `interfaces.right`, each read on its protruding strand |
| Permitted added DNA | `placements`, `foldback.geometry`, `basal.geometry` and each region's overhead limit |
| Available methods and materials | `enzyme_catalog`, each region's `enzymes`, and `materialization` |

The example permits left AGTC and right AACC or AGTC, with fixed geometry and
materials. Use it to learn the file format, then set permissions for your own
design. For AGTC/AACC alone, set `targets.right_words` to `["AACC"]`.
For all four-base pairs, use `targets: {}`: 256 words per side, or 65,536 ordered
pairs. Length bounds cap acceptable scaffold additions; execution limits control
how much of that coupled space HOP examines.

The [request reference](../reference/interface-survey-search.md#declare-the-molecular-domain)
defines every field, including primer policies, joint placements and recognition
requirements. This survey accepts an exact stem. For a hairpin endpoint or other
scaffold requests, use [scaffold discovery](discover-product-scaffolds.md).

## 2. Evaluate complete preparations

```bash
hop-design construction survey evaluate survey.json --index survey.sqlite \
  --max-evaluations 4 --local-nodes 1000 --local-realizations 1000 \
  --release-site-pairs 1000
```

The command creates a checkpoint and reports supported, excluded, unresolved and
unexamined pairs. A supported pair has a complete modeled preparation. An unresolved
pair needs more evaluation; it is not a finding of impossibility.

With the unedited example, AGTC/AGTC completes and AGTC/AACC is excluded under its
fixed permissions. To practice the successful handoff below, use AGTC for the
right-end filter. For your own design, retain the ends you need and choose the
geometry and material permissions you can accept.

Repeat the command with `--resume` to continue. Keep the request, HOP build and
per-evaluation limits unchanged; `--max-evaluations` sets the additional work for
that invocation. A changed molecular request needs a new checkpoint. See
[search limits and recovery](../reference/interface-survey-search.md#evaluate-and-resume)
for resource stops and larger surveys.

## 3. Explore the same results visually or programmatically

```bash
hop-design construction survey view survey.json --index survey.sqlite --out survey-view
```

Open the printed local address. The parameter key connects the molecular regions
to the parallel-coordinate axes. Click a value or drag a numeric range to filter
complete preparations. Click a trace to show its full nucleotide-resolution route.
At fit scale, ordinary scrolling moves the page. Pinch or Ctrl-wheel to zoom, then
pan to inspect bases. **Fit route**, Home or 0 restores the whole construction.
Tab enters each axis or molecular region; arrows move among its values or bases.
Enter applies a plotted value or opens its choices. Camera movement never changes
the query or selected preparation.

Each path represents a complete preparation. Values with support elsewhere in the
survey stay visible when a filter rules them out. Axis labels currently keep
unwitnessed values unresolved until the whole survey is exhausted. For a specific
pair's exclusion, inspect its recorded outcome with `construction survey inspect`.
Browsing filters recorded options; run `evaluate --resume` to search further.

The **Query, exact selection and CLI** disclosure saves `query.json` and
`selection.json` for the same work through the command line. **Reload checkpoint**
loads newly evaluated results. Changing the camera leaves the query and selection
unchanged. An excluded preview stays visible, with retrieval disabled.

For CLI or Python use, save your filter as `predicates.json`:

```json
{
  "schema": "hop.interface-survey-query/v1",
  "parameters": [
    {"key": "left_end_word", "values": ["AGTC"]},
    {"key": "right_end_word", "values": ["AACC"]}
  ]
}
```

```bash
hop-design construction survey query survey.json --index survey.sqlite --query predicates.json
```

Inspect `matching_preparations` and the returned paths. To compare end proximity
while holding both words fixed, add a `left_gap` or `right_gap` predicate with
`minimum` and `maximum`. If nothing matches, check coverage: continue an unresolved
search, or explicitly revise permissions after an exhausted exclusion.
HOP does not substitute other ends for you.

## 4. Select once, inspect the route, retrieve the parts

Use the browser's saved selection, or select a returned path by its `target`,
`step` and `materialized_realization_id`:

```bash
hop-design construction survey select survey.json --index survey.sqlite \
  --query predicates.json --target TARGET --step STEP --identity MATERIALIZED_ID > selected.json
```

Replace the three uppercase placeholders with values from that matching path.
To try one matching preparation without copying its address, use a reproducible
sample instead:

```bash
hop-design construction survey sample survey.json --index survey.sqlite \
  --query predicates.json --seed 23 > selected.json
```

Sampling chooses a complete preparation, not independent axis values or a ranked
best design. With no match it returns an error; shell redirection can leave an
empty file, so proceed only after a successful command.

The same selection drives the figure, route and preparation:

```bash
hop-design construction survey query survey.json --index survey.sqlite \
  --selection selected.json --out selected-figure
hop-design construction survey atlas survey.json --index survey.sqlite \
  --selection selected.json --out selected-atlas
hop-design construction survey retrieve survey.json --index survey.sqlite \
  --selection selected.json --out selected-preparation
```

Use a new output directory for each export.

| Open | What it provides |
| --- | --- |
| `selected-figure/figure.pdf` | Molecular parameter key and parallel coordinates with the selected trace |
| `selected-atlas/projection.pdf` | All recorded processing states across larger pages, with nucleotide text at least 8 pt at native size |
| `selected-atlas/projection.svg` | The same full route for zooming |
| `selected-preparation/preparation/oligos.csv` | Exact source, adapter and primer specifications |
| `selected-preparation/preparation/report.md` | Preparation details and conditions still to assess |

Print the atlas at native page size to keep every base readable. Atlas inspection
and retrieval replay the selected preparation. Destination compatibility,
fragment recovery and reaction performance still require experimental assessment.

## Use the same query and selection in Python

```python
import json
from pathlib import Path

from hop_design.construction import load_interface_survey_choices

pool = load_interface_survey_choices("survey.json", "survey.sqlite")
predicates = json.loads(Path("predicates.json").read_text())
choices = pool.query(predicates)
selected = pool.sample(seed=23, query=predicates)
Path("selected.json").write_text(json.dumps(selected, indent=2) + "\n")
```

The saved selection works with the CLI commands above. With no match, `sample`
raises before writing it. Retain `pool` for repeated fast queries; load it again
to include newly evaluated results. The [API reference](../reference/python-api.md#interface-surveys)
also covers explicit selection, atlas inspection and retrieval.

## Verify or compare a result

```bash
hop-design construction survey verify survey.json --index survey.sqlite
hop-design construction survey atlas survey.json --index survey.sqlite \
  --selection selected.json --reference-selection reference.json --out compared-atlas
```

`verify` replays every recorded evaluation for aggregate coverage claims. The
comparison command uses two saved selections to mark changes in the molecules and
materials across the route. Ambiguous base correspondence remains marked.

For detailed [coverage and search semantics](../reference/interface-survey-search.md),
[query and selection behavior](../reference/interface-survey-results.md), or
[CLI options](../reference/cli.md#complete-scaffold-options), follow the linked references.
