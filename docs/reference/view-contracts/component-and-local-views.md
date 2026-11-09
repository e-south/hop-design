# Component and local construction views

Build component views and read local construction projections without changing the
molecular records they present.

Return to the [view contracts reference](../view-contracts.md).

`WorkflowView` (`hop.workflow-view/v1`) defines the molecular content of a
visualization: ordered panels, strand-aware sequence tracks,
typed feature spans, and explicit pair calls. Before rendering, validation checks
that referenced sequence tracks exist and that feature spans and pair positions
lie inside them.

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
# Render the repository examples using the shared view implementation.
uv run python examples/render_component_views.py --out build/component-views
```

Or build views from already-derived mechanics:

```python
# Use the same view contracts from Python.
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
Use JSON for renderer-independent review and interoperability, and SVG for the
rendered view.

## Local construction projections

Payload-centered foldback and basal discovery also produce tables and drawings
of their local search results. These projections retain the source result's
sequences, measurements and search scope:

- `hop.foldback-feasibility-landscape/v5` records every exact foldback local
  realization from one unpartitioned search;
  `hop.foldback-feasibility-landscape/v6` carries the same relation for one
  declared sequence-domain part and includes its exact part scope;
- `hop.basal-feasibility-landscape/v6` records every exact basal local
  realization from one unpartitioned search as a local pairing and upstream
  completion obligation;
  `hop.basal-feasibility-landscape/v7` carries the same relation for one
  declared sequence-domain part and includes its exact part scope;
- `hop.basal-minimum-overhead-matrix/v3` records the smallest proven local
  retained overhead for every declared basal nickase by future Type IIS action
  cell, while distinguishing complete infeasibility from unresolved cells;
  `hop.basal-minimum-overhead-matrix/v4` carries the same relation for one
  declared sequence-domain part;
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

Basal feasibility rows expose `nick_boundary_from_payload` in the signed
payload-forward source frame. For clone-bearing local queries they also carry
`payload_end_offset_bp`, `future_reference_cut_from_payload`,
`future_complementary_cut_from_payload`, and the exact future side, polarity and
cohesive-end sequence. These cuts describe an obligation for a later molecular
state, not cleavage in the current local state. `pending_adapter_end_bases`
lists exact position/base obligations beyond the constrained local adapter span;
the full annealing requirement remains separate. Local `retained_overhead_nt`
continues to measure the PCR-intermediate accounting interval.

Complete summary rows expose actual endpoint strand lengths in nt and paired
positions in bp. Only accepted released endpoints carry left and right
`payload_end_offset_bp` measurements, derived from their two cuts and verified
payload features. Rejected or unfinished continuations carry no invented
endpoint measurements. JSON and CSV preserve these distinctions.

Foldback feasibility rows distinguish total paired arm `A`, nick displacement
`D`, and post-nick self-pairing arm `R`. The latter counts observed pairs whose
two bases belong to the same released fragment. It is not an additional arm
added to `A`. Each row links to its exact local realization and exposes:

| Field | Physical authority and unit |
| --- | --- |
| `annealing_arm_length_bp` | Total added paired arm `A`, in bp. |
| `junction_offset_nt` | Nick displacement `D` within that arm, in nt. |
| `post_nick_arm_length_bp` | Observed same-fragment pairs `R=A-D`, in bp. |
| `loop_length_nt` | Unpaired cap length `C`, in nt. |
| `exposed_tail_length_nt` | Released active strand from its 5′ end to its nick-relative boundary, in nt. |
| `source_extension_length_nt` | Distance from the mapped foldback payload boundary to the controlled terminus on the source reference, in nt. |
| `retained_foldback_length_nt` | Number of retained non-payload positions in the ligated foldback path, in nt. |
| `source_payload_boundary`, `source_nick_boundary`, `source_terminus_boundary` | Zero-based boundaries in the exact source-reference coordinate frame; strand and source orientation accompany them. |
| `retained_foldback_start`, `retained_foldback_end` | Half-open retained interval in the ligated strand's 5′→3′ coordinates. |

The source tail interval lies between the nick and controlled terminus; the
source extension lies between the payload boundary and controlled terminus.
Their source-reference order reverses with the physical nick strand. Both
source-terminus and separately cleaved-terminus local programs carry these
measurements; local program support does not imply complete-route eligibility.
For `A=6, D=2, C=4`, the measured values are `R=4` bp, a 12-nt exposed tail,
a 14-nt source extension and a 16-nt retained path. Moving `D` at fixed `A,C`
does not lengthen that retained path. The general projection permits `R=0`;
it does not impose a biochemical minimum for the post-nick arm.

When local execution declares a `sequence_partition`, every projection carries
its exact part count and zero-based part index. JSON and CSV expose those typed
fields, while SVG titles and metadata describe only the declared part. One
complete or infeasible part never represents an exhaustive whole-domain search;
aggregate coverage requires every verified, disjoint part.

These projections record local feasibility under the declared molecular model.
Complete composition checks selected local solutions together with route
materials and endpoint requirements.

### Teaching example: two bounded local neighborhoods

A fixed payload can leave two independent local construction questions.
Declare finite coordinate and action domains before searching, retain all
exact local solutions allowed by the execution bounds, and select an example
from those results. The selected example must not define which alternatives
were allowed into the search.

For the basal neighborhood, plot nick displacement `n` in nt against final
paired gap `e` in bp. Moving the nick need not move the eventual assembly end.
State the full association obligation `a` separately, along with the locally
constrained pairing window and its permitted noncanonical pairs. Use separate
panels for each pairing cap so readers can see which cap each result uses. A
count of end identities is a different question from whether any local solution exists.

For the foldback neighborhood, a direct search-coordinate plot uses total
added paired arm `A` in bp against cap `C` in nt, with one panel per nick
displacement `D`. A structural view may instead use the reported post-nick arm
`R`. At fixed `D`, the supported model relates them by `R=A-D`. For example,
`A=6,C=4,D=2` has `R=4`; this is a coordinate illustration, not an assertion
that a particular payload or enzyme supports that point. Holding `A,C` while
varying `D` preserves the retained path, whereas holding `R,C` while varying
`D` changes the required total arm. Read achieved measurements from the physical
projection rather than inferring them from a sketch.

A plotted point aggregates an explicitly named set of requests. A filled point
means at least one exact member exists among those requests. An open point can
mean absence only when every included domain has exhausted. An empty partial
search remains unresolved. A positive point may still have incomplete
alternative coverage. An exhausted traversal that generated no candidate
should be distinguished from evaluated candidates that failed constraints.
Coordinates outside the declared domain are unevaluated. Every point should
retain its request, result, and exact
member identities so the aggregate can be inspected.

If a plot collapses displacement, strands, orientations, or action choices,
its legend must explain what a point establishes: “some searched choice works.”
A catalog union does not prescribe applying every enzyme together. Neither
the shape of the feasible region nor the size of the chosen domain establishes
a global optimum or a complete route. Material preparation and endpoint
verification remain separate continuation questions.

## Source-partition projection

`hop.source-partition-certificate/v1` projects one explicitly selected
accepted source-partition realization. It preserves every top- and
bottom-strand fragment, its source-coordinate interval, required or
sacrificial disposition, physical-end or cleavage boundary, contributing
enzyme identity, and the complete preferred-to-absolute threshold ladder. The
selected maximum is the least permissive successful threshold established by
the canonical source-partition authority.

The SVG aligns both strands in source coordinates, labels their physical
polarity, and shows exact cleavage bonds rather than recognition-site starts.
The CSV is a tidy fragment relation with the threshold evidence repeated as
canonical JSON. The projection records the selected partition under its declared
cut geometry.
