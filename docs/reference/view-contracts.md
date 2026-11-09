# Workflow view contracts

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

## Complete construction projections

`hop.hairpin-portrait/v1` projects one explicit accepted realization's joined
hairpin. Actual intramolecular contacts and source lineage locate the supplied
stem, loop-side extension, open-side contacts, terminal unpaired tracts and
covalent joins. Noncanonical open-side contacts remain explicit: a contact
count does not assert canonical base pairing. The supported topology is one
contiguous antiparallel stem and unpaired loop in a single joined strand.
Bulges, branched pairings and unsupported source orientations raise rather
than receive an approximate drawing.

The state is `ligated_product` for a direct endpoint and `adapter_ligated`
for a PCR-bearing route. `later_release`, when present, names the exact
`clone_ready_duplex` state and its recorded cohesive ends. Hairpin dimensions,
source lengths, nick offsets and post-release flank spacing are separate measurements.
The same HOP-owned achieved-state descriptor checks optional hard scaffold
requirements during complete composition. Rejected candidates retain exact
materialized evidence and per-dimension mismatches; they never enter accepted
groups or the selectable gallery. Requirements and observations are replayed
when the result is loaded.
The atomic portrait packet includes its result-bound selection and exact
preparation; a projection is never a substitute for its verified bundle.

`hop.complete-construction-summary/v5` is the lossless tabular receipt over one
verified complete result. Its rows preserve the exact examined Cartesian
prefix—the initial portion of the declared combination order that was evaluated.
Accepted rows carry materialized route, achieved-geometry,
final-product, endpoint, and material facts; rejected and truncated rows carry
evidence only. Counts, failure partitions, material totals, group membership,
and truncation evidence replay the source result exactly.

`hop.construction-navigation/v2` extends the summary v5 relation with typed
foldback and basal geometry, exact relaxation state, the sorted enzyme IDs from
the declared cleavage programs, retained non-payload sequence, and endpoint
topology. Rejected and truncated dispositions, accounting, failures,
provenance, and claims remain in the nested summary. Geometry groups
describe the shared achieved geometry and retain every exact member identity;
no representative is selected. Renderer evolution does not alter the
construction result or bundle authority.

`hop.complete-construction-trajectory/v5` embeds the exact source preparation,
selected source-partition certificate when present, and chronology of one explicitly
selected accepted materialized realization. It has no CSV form
because it is a structured molecular-state sequence rather than a table. The
public operation requires `materialized_realization_id`; HOP never selects an
exemplar from canonical order.

The public `ConstructionProjection` packet provides canonical JSON,
deterministic SVG, and CSV when the projection defines a table. Packet writing
is atomic and create-only. The packet carries its projection schema, projection
identity, source-result identity, and renderer version while keeping the raw
projection model internal. Formats are rendered when requested; a JSON-only
navigation query does not construct unused CSV or SVG bytes.

## Complete preparation inspection

`MolecularStateInspection` projects one verified recorded state. Base addresses,
ancestry and contacts remain authoritative regardless of layout. Typed operation
annotations bind recognition spans, orientation, reference/complement cut offsets,
and displayed base addresses to the recorded reaction boundary mapping. Offsets
are zero-based precursor boundaries; recognition spans are half-open. Applied nick
boundaries may connect adjacent positions on different covalent fragments.

A layout frame is another recorded state with identical unique material positions
and pairing edges, but fewer covalent components. It supplies coordinates only.
The displayed state supplies every strand path, covalent break and contact. With
no matching frame, deterministic strand ordering keeps layout independent of input
tuple order. No contacts are added to denatured or selected-fragment states.

Molecular neighborhoods have distinct region fills with dark nucleotide letters.
Their bands follow continuous curves through the base centers. Adjacent regions
share a half-base boundary and tangent; a visual curve never adds a covalent bond
between separate strands. Browser motion recomputes the same curves from the
moving base addresses.
The compact teaching hairpin uses these same bands, base typography and site
contours. The band carries the backbone visually; addressed backbone edges remain
in the SVG without a second dashed texture. Separate strands leave a visible gap
even when their terminal bases occupy adjacent positions.
The hairpin/trace detail accompanying a similarity landscape uses larger labels
for a column in a paired seven-inch plate. Its axis labels remain at least 7 pt
at a 246 pt panel width; broader parameter sets use measured continuation bands.
The column detail places its loop-size label below the cap, leaving more width
for the molecule, and reserves space between the molecule and trace for a panel
letter. Nucleotide type is fitted to measured glyph widths; material letters are
centered on their recorded drawing positions. Standalone parameter figures retain
their full-width profile. Exact base addresses are unchanged. A composed plate
must still check its final scaling and provide full-resolution or continuation
exports for base readability.
Recognition sites use lightly filled, shallow-rounded bands slightly taller than
the strand. Their shape follows the same base path, including handle bends.
Enzyme names identify the site without a competing direction arrow; recorded
orientation remains available in the projection and SVG metadata.
Triangles and short boundary strokes identify strand-specific cuts; hollow marks
are planned operations and filled marks are applied operations. Persistent site
footprints follow recorded ancestry separately from the active operation. An
asterisk and dashed outline mark a partial or unresolved footprint; its title
carries the exact mapping and substrate eligibility. The route names enzymes at
their first mapped appearance and at acting steps. Every mapped footprint remains
visible. A printed key carries the color bindings and warning notation into both
the full plate and continuation pages. The renderer's `site_labels="all"` option
retains repeated names for detailed review.
Achieved interface brackets belong to the released endpoint and retain exact end
sequence, polarity and cut-derived paired gap. Annotation addresses outside the
shown state fail validation. Exporters draw these projections without scanning
sequences, inferring enzymes, or modifying molecular authorities.

The route uses named, editable SVG groups for stages, strands, primer inputs,
sites and cuts. A strand is ordered 5′ to 3′ regardless of its position on the page.
Primer arrows contain the exact input sequence and remain annotations, separate
from the recorded state's nucleotide inventory. A derived template does not become
an invented annealed intermediate. A complete recorded binding glyph replaces its
duplicate sequence-list entry and shows the input's terminal chemistry. Inputs
without such a glyph retain their sequence list. Comparison records and order
tables remain unchanged.

The renderer accepts `presentation="assembly"` for a shorter assembly drawing.
The default `"complete"` presentation and the atlas JSON retain every recorded
state. When the recorded cleanup chain is present, the assembly drawing skips
the separate denatured and selected-fragment scenes and shows **Retained and
annealed**. Its **Heat · cleanup · reanneal** arrow retains all three transition
identities in `data-transition-ids`, preserving the recorded route in the shorter
drawing.

Assembly scenes share the joined hairpin's drawing frame wherever material
ancestry gives an unambiguous correspondence. Each scene keeps its own strands,
contacts, cuts and bonds. An incoming adapter uses its later associated shape,
displaced from that position. The forward hairpin primer appears beside the
handle with **after copying**, since its binding template is the derived copy.
Incoming materials have `data-staged-material` and `data-input-base-index`;
they never acquire molecular occurrence addresses or premature pairing marks.
When exact placement cannot be established, the complete input listing remains.
Primer ribbons have an integrated directional wedge beyond their final base.
The template-facing edge continues flat into the tip; the shoulder flares outward.
Both primer inputs use the same normal clearance along straight and bent handles.
That drawing offset does not change binding coordinates or 5′→3′ orientation.
Strands, incoming adapters, primers and site bands share shallow rounded corners;
actual strand ends remain separate across an unligated junction.

Scene bounds include bases, primer arrows and placed labels. Labels can use nearby
side, upper or lower clearance; the shared placement domain
includes bases, cuts, termini and other labels. Two chronological
columns precede centered wide finishing states, without scaling nucleotide spacing.
Operation names sit beside large arrows in one row. Column transitions use a
continuous rounded connector with an arrowhead at the destination.
Titles are unnumbered. Measured scene edges and arrow endpoints use equal
clearance, with separate space reserved for the column turn before the wide finish.
The route's native print scale is 0.5 pt per drawing unit: bases are 8 pt, molecular
labels 24 pt and stage titles 28 pt. Seven-inch continuation pages have their own
type budget and retain every state-base occurrence exactly once. Full-route SVGs use the same geometry as
browser inspection; captions and input orders remain separate from molecular facts.

### Browser controls

The browser keeps the choice plot and selected molecular route together. On a
pinned hairpin, click a labeled feature, such as the loop or added pairing, to
read its definition and current value. **Color by** shows that feature across the
existing map. **Filter to** narrows complete preparations to the displayed value.
Neither action changes the search permissions. Escape closes the feature without
closing the inspector, and keyboard focus offers the same actions.
Paths shared by several preparations open a chooser. Materials, fixed properties
and search coverage sit below the figures. The same facts remain in static exports. Tab enters
an axis or molecular region. Arrow keys inspect its values or bases. Enter applies
a choice. At fit scale, scrolling moves the page. Pinch or Ctrl-wheel zooms into
the molecule, after which scrolling pans it. **Fit route**, Home or 0 restores the
whole route. These camera operations leave the query and selection unchanged.

The short, wide plot fits the desktop viewport. Values sit directly on their axes
in rounded nodes; paths meet those nodes. At 1,200 px it can show all 24 loop words
in the open-envelope example. Height is capped at 368 px; denser domains prioritize
selected and supported labels while retaining every coordinate and path. Literal
values wrap rather than becoming indistinguishable ellipses. Focus and **Browse…**
provide remaining labels and the full domain. Resizing changes only presentation.

### Molecular event grammar

The teaching hairpin and route use the same continuous strand contours.
Recognition outlines follow those curves at their recorded base boundaries.
In the teaching view, repeated sites on the same side can share an enzyme name
and leaders. Every addressed footprint remains present; complete sites and
partial or unresolved sites keep distinct labels. Opposite sides remain separate.
Noncanonical contacts have an open diamond; Watson–Crick contacts retain a simple
bond. Cut triangles distinguish planned (hollow) from applied (filled) cleavage;
applied cuts also expose the break. A bridge marks a recorded ligation bond.

Route termini show 5′/3′ direction and explicit phosphate marks. Unmarked termini
are hydroxyl ends, as stated in the printed key; exact chemistry remains in the
projection and addressed SVG metadata. Primer names and chemistry share one
measured annotation block, including in continuation-page exports. Released-end
labels show the recorded word in 5′→3′ order and its gap to the supplied stem.

Single-base parameter connectors mark their exact origins. A contact count can
link to its individual recorded contacts, rather than a whole neighborhood.
These marks do not add choices, contacts, cuts or preparation witnesses.
