---
doc_id: hop-view-contracts
title: Workflow view contracts
intent: Define renderer-independent scientific views and their generated artifacts.
audience:
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: reference
---

# Workflow view contracts

`WorkflowView` (`hop.workflow-view/v1`) is the scientific authority for a
visualization. A view contains ordered panels, strand-aware sequence tracks,
typed feature spans, and explicit pair calls. Referential and coordinate
validity are checked before rendering.

Molecular sequence fields are 5′→3′. Released-product tracks therefore display
as 5′→3′ regardless of literal strand. A coordinate-aligned precursor-bottom
track is explicitly 3′→5′; it is a display transformation, not stored molecular
state.

| View kind | Required panels |
| --- | --- |
| `foldback_junction` | folded junction only; no nicking state asserted |
| `foldback_qa` | source sequence, resolved junction, folded junction |
| `released_workflow` | precursor, released fragments, origin-anchored foldback |
| `basal_pairing` | paired basal junction only; no terminal nick asserted |
| `basal_terminal_nick` | pre-terminal nick, post-terminal nick |
| `method_trajectory` | the eight derived states of a complete named method plan |

Run the complete component example:

```bash
uv run python examples/render_component_views.py --out build/component-views
```

Or build views from already-derived mechanics:

```python
import hop_design as hop
import hop_design.views as views

foldback_view = views.build_foldback_view(foldback_evaluation)
basal_view = views.build_basal_view(
    basal_evaluation,
    nicked_strand=hop.Strand.TOP,
)
svg_bytes = views.render_workflow_svg(foldback_view)
```

Use `build_foldback_junction_view` and `build_basal_pairing_view` when the
components are known but a processing route is not asserted.

The dependency-free SVG renderer consumes only `WorkflowView`. It does not
recalculate pairing, cuts, spans, strand state, or eligibility. Equivalent view
JSON therefore produces byte-identical SVG.

Explicit-component bundles include route-neutral foldback and basal view
JSON/SVG. A design with an explicit terminal-nick request receives the basal
processing view. A design with a release projection also receives the
released-workflow JSON/SVG.
The JSON is the renderer-independent review and interoperability surface; the
SVG is a deterministic convenience artifact. Neither is experimental evidence.

## Local construction projections

Payload-centered foldback and basal discovery also support a narrower family
of local scientific projections:

- `hop.foldback-feasibility-landscape/v3` records every exact foldback local
  realization from one unpartitioned search;
  `hop.foldback-feasibility-landscape/v4` carries the same relation for one
  declared sequence-domain part and includes its exact part scope;
- `hop.basal-feasibility-landscape/v4` records every exact basal local
  realization from one unpartitioned search as a local pairing and upstream
  completion obligation;
  `hop.basal-feasibility-landscape/v5` carries the same relation for one
  declared sequence-domain part and includes its exact part scope;
- `hop.foldback-overhead-frontier/v1` and
  `hop.basal-overhead-frontier/v1` record unpartitioned absolute
  retained-overhead levels; `hop.foldback-overhead-frontier/v2` and
  `hop.basal-overhead-frontier/v2` carry one declared part, complete or
  partial level accounting, and observed rejection categories.

Each projection carries its source-result identity, renderer version,
provenance, and claim boundary. A projection is verified against its exact
source result by rebuilding the typed relation and requiring canonical
equality; a resealed subset, reordering, or invented row is rejected. JSON,
CSV, and SVG renderers preserve that relation without ranking candidates or
recalculating molecular state.

When local execution declares a `sequence_partition`, every projection carries
its exact part count and zero-based part index. JSON and CSV expose those typed
fields, while SVG titles and metadata describe only the declared part. One
complete or infeasible part never represents an exhaustive whole-domain search;
aggregate coverage requires every verified, disjoint part.

These projections establish local feasibility only under the declared
molecular model. They do not establish a complete construction route,
physical construction, quality control, biological activity, or empirical
enzyme performance.

## Complete construction projections

`hop.complete-construction-summary/v2` is the lossless tabular receipt over one
verified complete result. Its rows preserve the exact examined Cartesian
prefix: accepted rows carry materialized route, achieved-geometry,
final-product, endpoint, and material facts; rejected and truncated rows carry
evidence only. Counts, failure partitions, material totals, group membership,
and truncation evidence replay the source result exactly.

`hop.construction-navigation/v1` is a narrow non-authoritative overlay around
the unchanged summary v2 relation. Its accepted-route records add only typed
foldback and basal geometry, exact relaxation state, the sorted enzyme IDs from
the declared cleavage programs, retained non-payload sequence, and endpoint
topology. Rejected and truncated dispositions, accounting, failures,
provenance, and claims remain solely in the nested summary. Geometry groups
describe the shared achieved geometry and retain every exact member identity;
no representative is selected. Renderer evolution does not alter the
construction result or bundle authority.

`hop.complete-construction-trajectory/v3` embeds the exact source preparation and chronology of one
explicitly selected accepted materialized realization. It has no CSV form
because it is a structured molecular-state sequence rather than a table. The
public operation requires `materialized_realization_id`; HOP never selects an
exemplar from canonical order.

The public `ConstructionProjection` packet provides canonical JSON,
deterministic SVG, and CSV when the projection defines a table. Packet writing
is atomic and create-only. The packet carries its projection schema, projection
identity, source-result identity, and renderer version while keeping the raw
projection model internal. Formats are rendered when requested; a JSON-only
navigation query does not construct unused CSV or SVG bytes.

Complete projections are reversible views, not authority bundles. They cannot
establish physical execution, recovery, destination compatibility, QC,
activity, yield, empirical enzyme performance, or route preference.
