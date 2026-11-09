# Inspect recorded choices independently of their producer

Reopening a live discovery requires the HOP implementation that produced it. A
reader should also be able to inspect and retrieve captured preparations without
rerunning that implementation.

## Decision

`AtlasEdition` captures a chosen subset of complete preparations, their original
molecular packets and material handoffs. Its strict manifest inventories every file
with a digest and byte count. Reading verifies that inventory; lazy retrieval
rechecks requested bytes. Original producer and current renderer remain separate.
Capture accepts already verified choices and publishes them atomically to a new
destination. An edition cannot continue search or revise permissions.

An updated exporter can explicitly capture a completed released-insert discovery
through `freeze_design_choices(..., source_contract=...)`. The strict
`hop.recorded-design-source/v1` contract binds the original producer, snapshot and
all resolved input bytes. The operation owns one read-only survey reader,
retains per-member molecular verification, rechecks input bindings before atomic
publication, and returns only an immutable compact edition. A manifest-bound
`capture-origin.json` identifies the source and exporter separately. Ordinary
live admission and continuation still require their exact producer; source
contracts do not authorize search, schema migration or aggregate replay.

The explicit `compact=True` capture option writes `hop.atlas-edition/v2`.
Its index contains versioned molecular descriptors: summaries of recorded
molecular properties bound to the source snapshot. Each member retains its exact
material handoff in a deterministic, lossless ZIP.
Capture retrieves and verifies the selected authority before deriving its descriptor.
It does not render cohort-wide route drawings. The reader validates metadata and
inventory at opening, and checks each authority digest before access. This scope
is reported by `integrity`; it is not aggregate molecular replay. V1 opening still
checks every captured file. Archives are read without filesystem extraction,
reject unsafe or duplicate paths and non-regular entries, and have a 256 MiB
uncompressed per-preparation limit.
Atomic capture checks all published bytes, including compressed authorities.
`verify_integrity()` repeats that complete byte check independently of opening
and selection; its receipt explicitly excludes molecular replay.

The same `select`, `preview`, `atlas`, `figure`, `view` and `retrieve` operations
work on both formats. V2 renders a selected captured authority through the shared
projection and glyph layers. Its effective render policy is `current`, including
when a caller requests `captured`; the receipt explains that v2 contains no
original artwork. Material retrieval remains byte-identical. V2 descriptors are
checked against their selected authority before molecular rendering. The map can
read descriptors without opening all authority archives.

New live insert witnesses also record a versioned descriptor in their existing
integrity-bound projection. Landscape fitting consumes that index instead of
replaying every preparation. Scope and membership are checked at index access;
selected retrieval recomputes the entire projection from the replayed witness,
including the descriptor. Rehashing a false descriptor cannot authorize a changed
molecule. Older snapshots retain the existing admission path.

`design/construction/navigation` projects structural families and deterministic
samples from the existing choice index. Exact stage-qualified product identity
owns molecular membership. A structural descriptor groups products without
merging their identities or treating preparations as additional products. Feature
maps use recorded coordinates; mosaics use explicitly non-metric packing.
Equivalent coordinates share the parameter registry's canonical key.

Family projections return a query containing exact preparation membership bound
to the source snapshot. This optional restriction composes with parameter and
preservation predicates across live hairpin, live insert and edition choices.
It cannot be replaced by independent axis ranges. Empty membership is an empty
result; unknown members and mismatched snapshots fail. Omitted membership is not
serialized, preserving existing default query bytes and identities. Browser
family enclosures submit this query; they do not select a preparation implicitly.
Contextual geometry distributions count preparations with explicit recorded and
eligible denominators, molecular stages, units and missing values.

Guided sampling visits eligible families, products and preparations. Its versioned
receipt records query, stage, seed, history and pool digests. Replay recomputes the
choice before selection or retrieval. Ordinary seeded sampling remains unchanged.
A v2 view receipt additionally records processing focus, reference, camera,
landscape/molecular modes, grouping stage, layout, render policy and the next
sampling state. V1 receipts retain explicit defaults when read. Figure and
companion consumers pass this receipt through shared navigation, rather than
reconstructing defaults. A conflicting figure query is rejected.

`presentation.route` selects complete or assembly composition independently of
the molecular stage and renderer policy. Existing v2 views default to complete.
Current rendering uses the shared assembly map; captured rendering preserves its
original composition. An explicitly inspected cleanup state omitted by assembly
uses the complete drawing until inspection returns to All. Rendering metadata
records the effective composition and state counts. Cache identity includes this
presentation context; camera-only changes continue to reuse drawings.

The `loop` sampling strategy composes the existing regional-preservation query
with current eligibility, then samples a different recorded loop word. Its
`loop/v1` guided receipt retains the incoming query; its exact selection records
the effective preservation and membership restriction. The ordinary `families/v1`
strategy remains unchanged. A saved view can resume either strategy with the same
seed and history. This action never silently removes a locating filter.

An edition can also evaluate `DesignRefinementQuery` using captured complete
routes. Live and captured paths share the regional identity, material-role and
refinement projections. The edition verifies reference request/snapshot identity
and parses its captured routes without reopening discovery admission. Unsupported
route records produce an explicit preservation error, while captured artwork and
orders remain available. Derived regional facts are retained on that edition
instance; they are neither written back into the edition nor cached globally.

The primary `design view` command uses one inspection session for hairpin,
insert and edition objects. The HTTP adapter retains local-origin and request
token checks. JavaScript owns interaction and camera movement, not feasibility.
Failed preview operations retain the previous coherent selection. Preview files
are bounded by count and bytes and removed at shutdown; requested exports persist.
Legacy construction editors retain their explicit commands for compatibility.

## Consequences

Molecular similarity is a read-only projection owned by the same navigation
facade: `landscape()`, `preview()` and `neighbors()`. A versioned comparison record
separates shape, retained sequence and applicable receiving interfaces. Full-pool
normalization and nonredundant coordinates prevent filtering from changing the
meaning of distance. Comparison signatures do not replace molecular identities.
Distinct signatures are fitted once; every preparation remains addressable.
The optional `atlas` extra is required for fitting, never for reading coordinates.

Released-insert descriptors now record the sequence contributed by each unpaired
hairpin terminus to the final insert. Projection follows material lineage and
the recorded annealing portion of replacement PCR primers; independent primer
extensions do not establish template dependence. V2 comparison signatures replace
whole-tail lengths with retained-tail counts and ordered bases. Exact hairpin
measurements remain in the descriptor, and exact product/preparation identities
remain unchanged. Thus discarded handles can share a comparison position without
erasing their separate orders. Hairpin endpoints and saved v1 descriptors keep
their prior terminal meaning. Mixing these comparison scopes fails explicitly.

A captured landscape binds snapshot, membership, comparison definition, settings,
coordinates and projector identity. V3 views bind its digest; v1/v2 views retain
their previous meanings. Browser filters and saved-view restoration cannot fit
a different map. Public figure exports consume the same coordinate object.

Saving a view uses its already-read cohort answer. Captured landscape admission
may retain an immutable receipt on that edition instance: raw content digest,
snapshot, complete membership and semantic landscape digest. Fresh checked reads
precede reuse. The raw file digest never substitutes for the semantic view digest;
public landscape results remain independently validated and mutable results are
never retained. Ordinary member selection evaluates normalized predicates without
rebuilding cohort facets; regional-preservation selections retain their proof path.

Transient hover is separate from committed selection. The shared preview packet
contains the exact hairpin, parameter trace, compact identity metadata and
stage-qualified construction cost when recorded. Cost is projected from the same
molecular record; it does not trigger a material retrieval.
Captured editions read their verified artwork; live choices project one admitted
route. No complete route SVG or PDF is generated on pointer movement. The HTTP adapter
retains token and origin checks; the browser supersedes stale responses and
commits molecule and trace together. Teaching previews and route scenes have
separate 12-entry quotas within one 8-MiB file limit. Route browsing therefore
does not displace teaching previews merely by filling the entry quota; shared
byte pressure still evicts the oldest artifact.
The existing stage-qualified preservation query, not spatial proximity, certifies
the optional nearby-loop comparison. This verification runs on deliberate
inspector requests, outside the pointer path.

Inspector and publication compositions use the same glyph and parameter renderers
with distinct internal width and typography budgets. The inspector's axis SVG,
exact trace and feature connectors share that profile; its contents participate
in projection and cache identities. The main landscape remains separate from
the narrow inspection axes. Neither composition changes molecular coordinates
or the public request syntax.

Hover follows the same captured/current render policy as the pinned view. Current
artwork is recomposed before publishing the private inspection packet and its
manifest. Captured artwork and unsupported-schema fallback remain unchanged.
Publication exports keep their existing default profile and author-owned files
are outside this renderer's write scope.

The private scene projection requests one or two phases and resolves them to exact
state IDs within the inspected preparation. Unique-phase continuity is not base
correspondence. The response binds the snapshot, preparation, requested/effective
presentation, scene order and transition IDs. Missing phases remain unavailable;
explicit cleanup phases use the complete presentation when assembly omits them.
Subset rendering retains prior site introductions and global material disclosure.
Captured scene extraction preserves presentation ancestry and definitions.
Unrecognized ancestor transforms, nested viewports or nontranslation scene
placement report isolated-scene preview unavailable; the full saved drawing
remains available. A
validation error in a current projection raises; unsupported captured schemas may
report scene inspection unavailable. Public atlas export remains complete.

The browser opens the route stream after pinning. Only visible phase slots request
drawings, at most two per request, after the matching hairpin has committed.
Each response must match preparation, snapshot and inspection token and account
for every requested phase. Stale completions cannot reveal a scene. Fixed slots
preserve scroll during hover; a presentation change anchors to the same phase or
the nearest surviving phase. Four pinned SVG nodes support immediate restoration;
offscreen drawings are detached and page teardown releases the controller and
cache. Before the first pin, hover previews only the hairpin and parameter trace.

Frozen drawings and orders remain viewable after producer changes. Captured
artwork and current redraw are explicit policies; comparison does not implicitly
redraw a captured route. Unsupported current redraw retains captured artwork with
an effective-policy notice. Inventory checks establish
content consistency, not trust in an unknown publisher or new molecular validation.

The companion consumes public selection, figure, atlas, view and retrieval calls.
Its edition receipt wraps, rather than rewrites, the original handoff selection.
Article layout and scientific cohort selection remain caller responsibilities.
