---
doc_id: hop-adr-0050
title: Inspect a preparation without editing molecular intention
intent: Separate displayed states, conditional permissions and required membership while retaining one molecular authority.
audience: [maintainers, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-16
doc_type: explanation
---

# Inspection and required comparisons

An experimentalist may inspect the insert produced from a pinned hairpin without
changing what the pin means. The query stage continues to qualify constraints;
the inspection request names a preparation, recorded state and optional exact
molecular address. Inspection cannot select a preparation, reset a reference or
rewrite membership. Excluded previews stay identified until an explicit change.

`models/construction/variants/` owns strict requests. Admitted immutable routes
stay in `ScaffoldExploration` separately from serialized query facts.
`projections/inspection.py` follows recorded material ancestry and pairing;
`projections/neighborhoods.py` supplies one anatomical vocabulary to drawing and
picking. Exporters render that projection, and the viewport consumes its addresses.
No renderer aligns equal sequence words to invent ancestry or predicts conformation.
Source, cleavage, fragment, joined and copied states remain those of the verified
construction program. Unsupported states and unknown addresses raise.

Allowed variants are a union, while required comparison members are obligations.
`variants/comparison.py` binds requirements to the admitted query and original
discovery permissions, then delegates bounded assignment to `comparisons/grouping.py`.
It introduces no solver and performs no molecular search. Both discovery and edit
packets use the same verified-admission boundary. Missing members and unexamined
assignments remain visible. A compatible set is never selected automatically.

`variants/comparison_selection.py` re-admits the original source and re-evaluates
query, membership, molecular controls and material requirements before existing
portable-set assembly. Selection carries comparison decision provenance; its
member authorities remain the source of molecular truth. Export protects source
roots, and fresh retrieval cannot rely on cached browser observations.

Interface facts attach actual enzymes and cut-derived achieved distances to
preparations, separately from requested distances. Method names never create
product identities. Branch coverage preserves joint ends and distinguishes
local absence, examined continuation failure, unfinished work and query exclusion.

The CLI and loopback viewport call these public operations. Display state, query
stage and required set remain separate controls. Public recipes are
`examples/molecular-editing/conditional.py` and `navigation.py`; focused regressions
are `test_scaffold_inspection.py`, `test_variant_comparisons.py` and
`test_variant_editor.py`. Runtime measurements separate admission, first projection,
warm projection and retrieval. Study evaluation and manuscript selection remain
outside this package.

## Conditional preview and display geometry

`variants/preview.py` intersects an observed local variant with all active
constraints, including the focused pin. One compatible preparation can be
previewed; multiple preparations require an explicit label even if their products
are equal. Preview packets retain the query identity and no selected product.
Semantic phase selectors resolve independently for each preparation, with named
unavailable/ambiguous outcomes. Material focus transfers through exact shared identity, strand and index. Explicit
comparison focus may instead follow a unique named-region correspondence while
reporting changed ancestry. Ambiguous correspondence remains unassigned.

`projections/inspection_annotations.py` owns recorded operation addresses and
interface distances. `inspection_layout.py` chooses an existing equivalent pairing
frame. Export layout and overlay modules consume these facts separately; they do
not derive chemistry. Browser navigation, permission editing, comparative-set
membership and molecular inspection have separate modules. Browsing reuses admitted
immutable routes; retrieval still re-admits original sources. The public
`examples/molecular-editing/browsing.py` exercises this boundary.

## Continuous inspection contracts

`inspection_sites.py` projects route-recorded recognition footprints through
produced-material ancestry; `inspection_lineage.py` owns that resolution. Ordered orientation anchors retain precursor-reference direction when a folded
strand reverses on the page; unresolved anchors receive no guessed arrow. Presence
is separate from substrate eligibility and reaction timing. Missing, partial,
removed and repeated mappings remain explicit. `inspection_annotations.py` keeps
planned/applied cuts and achieved end gaps tied to their actual states.

`inspection_correspondence.py` distinguishes processing ancestry/copy relationships
from comparisons between preparations. It uses existing bounded regional sequence
correspondence, never whole-sequence guesses. Comparison addresses are not material
identities. `surroundings` controls name a stage and an excepted neighborhood;
changing the browsing focus cannot move these requirements. Unassessed regions do
not satisfy preservation by virtue of both being absent.

All inspected states use `inspection_scene.py` primitives and the same layout.
Bases, edges and fitted spans carry exact address membership. The browser's
`continuity.js` resolves only supplied links; `motion.js` interpolates coordinates
between recorded scenes; `camera.js` changes no query or preparation identity.
Copying can map one source to several displayed bases. Ambiguous mappings fade
with an explicit notice. Animation does not create chemical intermediates. Picking
waits for the static frame; rapid navigation uses latest-request presentation and
serialized HTTP mutations. `inspection_labels.js` gives molecular choice labels
without promoting preparation IDs into the primary vocabulary.

Repeated literal comparisons use a 64-entry cache keyed by both sequences, region
and coordinate spans; immutable comparison models retain ambiguity. Each viewer
cache holds at most 64 exact query/request-bound projections. Eviction removes
memory entries, not exported receipts; monotonic artifact destinations prevent
path reuse. Retrieval always re-admits sources and cannot use these caches as
selection authority. Python and SVG records remain useful without browser motion.

## Portraying verified records from another producing version

Molecular portrayal consumes the read-only `MolecularRouteView` protocol. The
normal API still admits a complete realization and includes its construction-cost
projection. `project_recorded_molecular_atlas` is a lower-level projection seam
for a caller that has already verified its original producing records. It retains
the supplied preparation identity, typed states, material bindings and coordinate
frames; it does not compile, select or confer current compiler authority.

Producing-version adapters and their replay receipts belong to the caller.
They must not invent missing release evidence or rename a cut-union projection as
a newer parent-core record. The atlas validates its state, transition and address
composition. Compiler-derived cost is absent on this path. Both paths use the
same molecular renderer; neither changes the original evidence package.

Atlas export can label only the recorded operations (`site_labels="operations"`).
All recognition footprints and their exact addresses remain drawn, with ancestry
status retained in SVG metadata and titles. Partial ancestry and repeated copies
describe footprint projection, not an unresolved required reaction. The default
full-label view remains available for inspection.

Terminal labels include the recorded hydroxyl or phosphate chemistry for states
and supplied materials. Formed joining bonds are projected from the two exact
precursor ancestry addresses onto adjacent product bases; a sequence alignment
cannot substitute for that correspondence. The rendering marks these recorded
bonds distinctly. A print page lists every state represented by its panels,
including continued portions of a state whose first panel is on another page.
