# Complete preparation views and inspection

Read the portrait, trajectory and molecular atlas of one verified preparation, including
its exact drawing and interaction contracts.

Return to the [view contracts reference](../view-contracts.md).

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
