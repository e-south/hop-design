# Performance and verification boundaries

Start with a request that returns a complete preparation. Measure discovery,
reopening, retained queries, the molecular atlas and retrieval separately. A fast
filter says little about the cost of finding or verifying its input molecules.

Pinning a molecule projects its exact states, comparison and construction cost,
but draws only the hairpin overview. Opening the route draws its processing
states. Both views use the same admitted records and bounded preview cache;
closing the inspection server removes its temporary files. Public `atlas()` and CLI
atlas exports still produce the complete route. Measure pinning and opening the
route separately: deferring artwork does not remove molecular verification.

Hover keeps one active preview and only the latest waiting choice. Leaving the
map, selecting a preparation or closing the page discards waiting previews;
already-running server work can finish but cannot replace the current view.
Inspection starts immediately through that bounded controller; a second debounce
timer must not add latency before a point can be inspected. Rapid target changes
replace waiting work instead of growing a request queue.
Clearing the browser artifact cache also invalidates pending cache admissions.
Measure server work and retained browser memory separately from stale-display
protection.

Panel-local loading preserves layout. Molecular panels retain the previous drawing
and trace in grey, with an explicit previous-preparation label and a top-left loading
indicator. These references are inert until the matching replacement commits;
materials and failed or empty panels remain covered. The existing drawing nodes
are reused without extra rendering, cloning or requests.
Pinning freezes the displayed preview until the committed drawing is ready,
including the first pin when there is no previous selection. Leaving a point while
that mutation is pending cannot clear the reference or expose an unfinished result.
The hairpin, exact trace and difference explanation commit together; route and
material panels cannot present another preparation as current. Loading adds no
request, timer or minimum display duration. Cached inspection can appear immediately.
Measure loading feedback separately from time to usable content.
If a combined preview fails, visible route slots enter the same explicit error
state instead of remaining in preparation. A stale failure cannot replace the
loading state of a newer preview. The retained drawings remain non-interactive.

Both map canvas renderers repaint retained points after context restoration. They
coalesce restoration into one animation frame and remove their listeners on
teardown. Recovery neither reloads the cohort nor changes the camera or selection;
ordinary hover still repaints only the selection layer.

The private scene-inspection endpoint accepts distinct names from the finite
recorded phase vocabulary, for one preparation. The browser submits the visible
scenes together so they share one molecular admission and projection. An absent
or ambiguous phase is explicitly unavailable. Only requested scenes are drawn,
while label introduction and incoming-material placement retain the whole route's
context. Measure authority access, scene drawing and cache reuse separately.
Scene composition keeps a native element tree through annotation, measurement
and placement. Serialization occurs at the export boundary, avoiding a second
document representation and a serialize/reparse cycle for each route scene.
The same molecular glyphs and addresses serve standalone and composed drawings.
After pinning, scrolling loads only visible scenes. Hover reuses those fixed
phase slots, identifies prior drawings immediately, and waits for the matching
hairpin before requesting scenes. No additional authority cache is retained.
The scene channel permits one active request and one latest pending request.
Leaving restores up to four cached pinned scene nodes; offscreen drawings are
detached. Changing route presentation anchors scroll to the inspected phase or
its nearest surviving neighbor. The full figure remains an explicit focus action.

Teaching previews and route scenes each retain up to 12 entries, sharing one
8 MiB transient file budget. Separate entry quotas keep scene requests from
evicting a small teaching working set; byte pressure still evicts the oldest
artifact across both. Each
new derivation reads the admitted authority; a cache hit reuses already-admitted
artwork and does not authorize retrieval. Saved artwork retains inherited style
and definitions when extracting a scene. Captured coordinate layouts that cannot
be isolated safely remain available as full figures and report scene preview
unavailable. Current drawing uses the same primitives
as the full route. Neither operation changes selection, query, camera or history.

Compact-edition pinning compares admitted routes before drawing the hairpin, so
it does not create and discard an initial overview. Selecting one member checks
its normalized predicates and full-pool membership without calculating every
axis's facet counts. Regional preservation still follows the complete proof path.
Saved similarity views reuse an immutable landscape-admission receipt on that
edition object: every access checks current file bytes, snapshot and full membership
before reusing the semantic digest. Public landscape calls still return independently
validated models; neither mutable models nor file paths confer cached authority.
Opening the map creates this receipt from the same checked bytes used to validate
and draw its coordinates. The first pin therefore avoids repeating that admission;
it still checks the current bytes, snapshot and membership. The receipt retains no
coordinate model and does not move a second validation into the opening path.
Captured descriptor indexes validate their complete JSON envelope and all molecular
rows in one pass. They keep strict row validation, edition membership, stem and
endpoint checks while avoiding per-row JSON serialization. Returned descriptor
dictionaries remain detached, and every access still checks the captured file bytes.
The first unfiltered query also retains immutable teaching metadata for individual
members. First inspection reuses those facts instead of projecting the full cohort
again. Filtered answers cannot populate this context, and caller mutations cannot
change it. This retains metadata already needed by inspection, not molecular
authorities; measure opening plus first pin when evaluating the tradeoff.

Compact hairpin preview passes its typed molecular projection directly to the
shared teaching renderer. It projects the source duplex, association, hairpin,
final product and enzyme precursors needed for teaching. Recognition ancestry
still follows the full route. The teaching projection retains exact inspections,
recognition footprints, parameter locations and cost without building unused
processing-correspondence maps or incoming-material placement. The complete
atlas still requires consecutive transitions and bound inputs. Preview neither
serializes nor validates that complete atlas again to draw one hairpin.
Each fresh preview still checks captured authority
bytes, descriptor agreement, snapshot membership and molecular identities. The
serialized renderer retains validation for external records. This reuse lasts
only for the current call; it adds no persistent molecular-model cache. The
compact-preview regression checks identical artwork, context reuse, unknown
membership, missing-transition rejection for externally serialized atlases, and
altered-archive rejection, and belongs to the presentation gate.

Compact-edition hover owns one lazily started rendering process. The parent checks
the selected archive and snapshot, then sends one route, its expected descriptor
and the minimal drawing context. The child validates the complete molecular record
and descriptor before calling the shared teaching projection and glyph renderer.
It never receives the cohort graph. Direct API/CLI figures retain the synchronous
path; live discovery and captured-artwork inspection retain their existing paths.

The worker accepts one active job, with no internal queue. A private pipe avoids
process-pool cleanup locks after a crash. A timeout or failed process discards that
process and pipe; an explicit retry starts a fresh renderer. Closing the session
stops rendering before waiting for the session lock, then removes temporary files.
Shutdown allows one second after terminate and one second after kill. There is no
silent fallback or alternate molecular authority. Measure cold process startup,
warm cache misses, parent-plus-child CPU and memory separately. Route-scene drawing
does not yet use this worker.

`test_inspection_worker.py` checks failure, timeout, concurrent work and teardown.
`test_isolated_preview.py` compares exact drawings and summaries and rejects altered
authority. Changes to that extraction/admission boundary require source verification;
browser-only changes still use the presentation boundary below.

Neighbor inspection ranks eligible descriptors with the prepared exact-distance
kernel and reconstructs preservation facts only for its returned membership plus
the reference. The browser first requests ranking without control verification;
the deliberate control action uses the same API with verification enabled.
Neighbor computation runs outside the session lock. Request identities prevent a
late cancellation from stopping newer work, and selection changes or teardown
cancel the current request. Deadline and cancellation checks occur between ranking
steps and major phases; they do not interrupt a molecular validator mid-call.

## Run the public lifecycle

Save a construction intent as `intent.json`; the [discovery guide](../guides/discover-designs.md)
describes its stem, product and optional scaffold constraints. Then run:

```bash
mkdir -p .artifacts
uv run --locked python scripts/benchmarks/design_lifecycle.py intent.json \
  --max-evaluations 4 --repeats 3 > .artifacts/lifecycle.json
```

The script checks repeatable selection, coverage, atlas content and handoff files.
Each trial uses a fresh temporary directory and removes it on success, failure or
interruption. Only the requested measurements remain. A request without a complete
preparation raises; it cannot produce a successful retrieval measurement.

The JSON records each phase's seconds, three-run medians, the executing producer
and process peak resident memory. Run before and after measurements in separate
processes with the same request, limits and environment. Source changes alter
producer-bound digests; use same-producer replay comparisons to establish artifact
equality and compare exact molecular identities across versions.

For diagnostics, add `--profile .artifacts/lifecycle.prof` or `--allocations`.
The profile output includes disjoint self-time groups and separately named
inclusive entry costs. Inclusive costs overlap; do not add them together or
interpret time spent in a validator as proof of which molecular phase caused it.
Profiling and allocation tracing add overhead, so measure latency separately.
Allocation tracing reports current and peak Python allocations per trial; resident
memory includes native allocations and is the high-water mark of the whole process.
Use `scripts/benchmarks/local_discovery.py` when the bottleneck is local enumeration.

## Reuse only the authority already established

| Boundary | Reuse allowed | Checks retained |
| --- | --- | --- |
| Bounded option generation | Identical successful local proofs within the call | Strict models, complete route, actual published files, all candidate outcomes |
| Saved discovery admission | Identical local proofs within the captured pool | File inventory, digest, producer, route and projection replay |
| Branch projection | Verified candidate receipts from that invocation | Binding to the selected preparation and branch |
| Candidate publication | Its fresh compilation, after staged admission | Actual published inventory, manifest and exact artifact bytes |
| Selected-set retrieval | Receipts from its one admitted snapshot | Membership, reference, material reuse and chemistry |
| Independent public load | No previous proof scope | Fresh admission and replay |

Local proof reuse is bounded to 64 entries and 8 MiB of canonical proof content.
The key includes the complete result, producer and replay policy. Changed inputs
must replay; failed results never enter the cache. Exiting or interrupting the call
discards the scope. No path, modification-time or process-wide verification cache
can stand in for these checks. See [reliability](../../RELIABILITY.md).

The focused checks are `test_construction_bundle_replay_cost.py` for replay and
byte parity, `test_local_replay_scope.py` for cache lifetime and limits, and
`test_lifecycle_benchmark.py` for interrupted-run cleanup.

## Scale comparison without expanding molecular permissions

Enzyme permission checks reject explicit allow-list, forbidden, reserved and role
restrictions before scanning catalog membership. Remaining candidates still require
a catalog entry. This avoids rebuilding a catalog-sized set per check, without a
new cache or changes to enzyme eligibility, catalog validation or search order.

Survey branch translation reuses the request's admitted, immutable enzyme catalog
instead of serializing and reparsing every entry at each new grid address. Derived
fields and the complete product still pass strict validation with typed tuples and
enums. Independent JSON admission continues to validate the full catalog. Branch
addresses, enumeration, canonical product bytes and the bounded product cache
retain their existing contracts. Cache accounting serializes the fixed catalog
member once per translator, then combines that byte count with each product's
remaining members. It still charges the exact complete canonical JSON size,
including escaped/Unicode text and separators; entry limits and eviction stay
unchanged. This retains one integer, not another catalog copy.

Fresh complete composition evaluates its permitted combinations and validates
the resulting molecular record once. It seals that internally generated result
for projections and packaging instead of immediately composing it again.
Externally supplied results, explicit verification and saved-file admission
retain full deterministic replay. The in-process receipt is tied to object
identity and canonical content; it is neither a persisted proof cache nor an
option for bypassing verification. Compare canonical records, stored objects,
coverage and cold continuation when changing this boundary. Measure discovery
separately from publication and reopening, which deliberately retain replay.

The necessary end-pair projection uses the same boundary: it retains admitted
enzyme provisioning while validating the derived local pairing constraints and
unpartitioned search request. Relation cache keys, molecular solving and resource
limits are unchanged.

Recognition-window conjunction normalizes each distinct base-choice tuple once
per call and replaces only positions touched by a site. Unchanged positions
share immutable tuples. Empty domains anywhere still reject the assignment;
overlapping windows and complemented copies constrain the same variable.
This avoids rebuilding mutable sets across the entire source for each short
site, without a persistent cache or changes to admitted sequences.

Hairpin continuation writes immutable pages of new candidate outcomes. It does
not copy prior preparations into each new snapshot. Independent admission still
verifies the selected history; page storage and restart time are distinct costs.
Explicit parameter or envelope revisions capture that history as one portable
authority. The selected page digest and all earlier preparation identities stay
unchanged.

Conditional handle completion records observed diversity classes in its versioned
cursor. The scheduling wave remains the first priority; unseen requested classes
break ties within it. This preserves finite reachability and reproducible resume.
Only complete compiler projections update observed classes. A frontier or observed
class bound stops computation without declaring molecular infeasibility.

The bounded foldback-admission probe also removes proven-empty cases from the
diversity rank calculation. Each requested shape therefore starts with its first
locally admitted representative; impossible earlier join positions do not make
that shape wait behind repeated representatives of another shape. Unknown and
unexamined cases retain their original costs, and proven-empty cases retain finite
fallback positions. This changes visitation, not permissions or complete-route
verification. Report gains and losses across both local neighborhoods: more
foldback breadth in a finite prefix can mean fewer basal alternatives in that
same prefix.

For diversity exploration, each admitted basal or foldback program starts at the
same local sequence depth. A second enzyme program does not wait behind every
geometry's first program merely because its population appears later in the roster.
This depth is a scheduling position, not a molecular length or biophysical score.
Exact program/member and Cartesian page addresses stay unchanged. The page merge
uses the existing frontier bound; exceeding it stops navigation explicitly, rather
than expanding an unbounded temporary list or rejecting a molecular family.
Ordinary first-result execution keeps its original page order. The preference
changes allocation, so compare useful molecular coverage per CPU-minute, not just
preparation counts or elapsed time for different returned molecules.

When the objective includes `loop_word` and a geometry has no authored exact loop,
the search chooses a different deterministic starting member within each admitted
foldback population. The canonical target, geometry and program address seed a
cyclic permutation; no sequence population is expanded to choose its start.
Every permitted member retains its original exact address and remains reachable.
The permutation is a diversity preference, not uniform molecular sampling, and
cannot certify an excluded or complete domain. Basal order, auxiliary completion
and complete-compiler verification remain unchanged. Exact authored loop words,
geometry-only objectives and ordinary first-result search retain their page order.
Storage for rotated program ranks obeys the existing frontier bound before sorting.
Compare later batches as well as the first prefix; report new loop words, retained
products, structural classes, compiler failures and cost separately.

Within each finite completion wave, allocation first favors an unrepresented
combination of requested structural coordinates, then an unrepresented exact
sequence. A loop-word objective uses its known length at the first level and its
exact word at the second. This prevents another word on a represented geometry
from masking unvisited geometries. The public objective and reported diversity
still count exact words. Only complete projections add observed classes; unknown
candidate words do not supply sequence evidence. Pending work remains reachable
and follows the same order after cold resume. Hierarchical feedback is recorded
in the `hop.context-group-seek/v7` cursor; older producer-bound records require
their original producer for replay.

Interface-diversity objectives also guide the outer target order. A deterministic
probe examines at most 16 basal frames per declared placement and 256 frames in
total, further bounded by the navigation budget. It samples the intersection of
joint necessary-end relations with the requested word permissions. Unknown or
resource-stopped relations retain ordinary traversal. Suggested pairs precede
the ordinary coverage fallback; the first canonical pair has no special priority
without a molecular suggestion or an explicit preparation preference. The latter
still takes precedence. The canonical target
addresses remain unchanged; the producer and saved objective bind the ordering
used for continuation. The progress report exposes probe counts, and the query
reports `joint_interface_relations/v9` for interface objectives. Within-target
policies remain `within_target/v6` for local-method objectives, `within_target/v5`
for loop words, `within_target/v3` for other foldback geometry and
`within_target/v2` otherwise. The objective parameters retain those distinctions
under the shared interface policy. Older producer-bound checkpoints still require
their original producer; this ordering change does not migrate saved work.
The bounded probe first spreads across authored basal-factor values, then retains
the original complete product as its lazy fallback. This prevents a short probe
from repeatedly using only the first nick offset. Joint end pairs still come from
the molecular relation, not independent choices of left and right words.
After a target has a complete witness, its priority key rises every eight
continuations, sharing work with further interfaces. For unresolved targets it
rises every 64 continuations. These are priority increments, not hard turn caps:
rank ties can keep the first unresolved target ahead for 128 evaluations.
These monotonically increasing priorities preserve the finite target roster and
are reconstructed from committed outcomes on resume. These shorter turns affect
only outer interface scheduling; first-result and within-target schedules keep
their original target turns.
The interface policy retains each proposed pair's known objective classes. Within
the same fairness wave, it favors classes not yet witnessed across the survey;
changing an unrequested end word alone does not establish requested diversity.
Only committed complete projections update this bounded feedback, which is
reconstructed on resume. Unknown classes remain eligible. These partial hints
affect outer target order only, preserving target-local molecular replay.
These are finite-budget preferences, not new molecular limits or support proofs.

Necessary end-pair screening traverses basal work once within its retained-DNA
bound, rather than rescanning the target roster at every possible overhead
level. Canonical offsets and the fixed pairing length make the retained overhead
monotone. The stream preserves the units and order of the explicit level-by-level
traversal and stops at the first offset above the bound. Individual-level callers
keep their existing behavior; no search permission or resource ceiling changes.

Necessary end-pair projection reuses output assignment masks within one placement
and sequence-set builder. Bases absent from the exposed ends share an output
mask, but still undergo pairing checks and consume the noncanonical-contact
budget. The cache ends with the projection; it does not reuse construction proofs.
Before building contact factors, the projection stages each contact's permitted
assignments and their noncanonical costs. A contact with no assignment, or a sum
of unavoidable costs above the declared budget, proves the projection empty.
Hidden bases and G:T wobble contribute to that bound. A contact with neither base
in the exposed ends contributes its minimum allowed cost directly: the contact
variables are disjoint, so a more expensive hidden assignment cannot add an end
word. Subtract those costs before the dependency-preserving DP over visible
contacts, and do not construct choices above the remaining mismatch allowance.
Staging retains at most sixteen assignments
per distinct combination of base masks and contact permissions within one call.
Identical options are derived once, but every position retains its permissions
and consumes its own mismatch budget. This does not introduce a persistent cache. Output-frame
validation and the builder's computation-limit checks remain in force. Compare
complete continuation records and memory as well as the isolated kernel timing;
the lower bound does not establish complete-route feasibility. Reduced work may
resolve a relation that previously exhausted the same computation allowance;
exhaustion still means unknown, not an empty relation.
Compare complete fresh and resumed discovery records when measuring this path.
Within one end-pair projection, each distinct enzyme definition and end requirement
resolves its cut program once. Different source lengths still derive and check
their own recognition and end placements. Reuse is keyed by the full immutable
enzyme definition, ends with the call, and leaves sequence-set budgets and
saved-record admission unchanged.
Source/adapter base permissions are also derived once per local domain, lazily
after the first compatible frame. Each evaluated handle pattern supplies its own
base domains and receives the same placement and pairing checks; only one local
permission tuple is retained at a time.

For a uniform upstream length range, necessary end-pair projection and endpoint
filtering of local source/adapter populations share the same longest-length
envelope when the endpoint forward primer adds no handle. With release
windows anchored to the payload, every shorter frame embeds in that longer
frame by preserving its suffix; the extra bases are independent existential
variables. The longest relation therefore equals the union over all lengths.
Both projections retain their original output variables and exact relations.
This reduction applies to necessary constraints only. Complete source-context
and material discovery still enumerate every permitted length. Added forward
primer handles retain the explicit length union: their fixed bases can supply
a recognition site available only in a shorter frame. Compare against explicit
per-length unions and preserve that counterexample when changing the reduction.

After placement checks, equivalent end-pair problems within one local domain
share a projection. The key keeps every local base mask and every observed
upstream mask, copy relation and complement orientation. Independent upstream
bases absent from the exposed ends are omitted; all original frame-length and
recognition checks run before that reduction. At most 128 projections are retained
for that domain and builder, then discarded. Eviction recomputes the same problem.
This reuses a necessary-condition calculation, never a complete construction or
an externally supplied proof. Distinct source lengths and exact material
completion remain available to ordinary discovery.

The invocation-owned basal-frame index retains at most 32,768 established
relations and 16 MiB of canonical relation content; Python object overhead is
additional. This allows a recurring placement set to survive between requested
end pairs instead of being evicted on every sweep. Target membership is checked
on each access, unsupported translations are not reusable rejection facts, and
the request and sequence limits remain bound to the index. Entry or byte pressure
evicts the least recently used frame without changing its answer. Nothing persists
between invocations. Measure cold construction, repeated access and whole-process
memory separately; a cache-hit improvement does not establish campaign throughput.

Multi-target completion now groups those relations into a shared basal screen
before target-local navigation. It derives every frame from the bound request,
groups identical relations, and maps each requested end pair to the matching
frames plus all unknown frames. Candidate coordinates retain the ordinary cost
and canonical-address order. Indexed navigation jumps directly to the next
candidate instead of traversing rejected basal coordinates and empty cost waves.
Cursor lookup uses binary search over the admitted ordered candidates without
materializing every candidate's cost key again. Candidate validation, cost ties,
foldback offsets and traversal order remain unchanged. The navigator derives
its fixed dimension sizes once when validating the candidate roster.
Uniqueness and ordering are checked in one pass over adjacent cost/address
keys, without copying the roster into a set and sorting it again. The check
rejects duplicate addresses and decreasing keys while retaining every domain check.
The complete compiler, local sequence choices and all foldback alternatives
remain unchanged. Navigation records bind the full frame-to-relation digest;
replay rebuilds it independently. No study roster or private data enters this path.
Within that screen, at most eight target/cost-order candidate lists are reused
across continuation steps. They hold references to existing frame coordinates;
eviction recomputes the same list. Target and dimension checks still run on
every lookup, and the navigator still validates the returned roster and checks
basal admission. This avoids repeated membership scans and sorting without
caching a complete-construction claim. Lists end with the discovery invocation;
profile their cold construction, reuse and memory separately from molecular solving.

Named release enzymes with identical modeled definitions can also share a
necessary relation through the existing bounded cache. Both basal and release
permissions must explicitly select the same allowed singleton before lookup.
Only its two role references are normalized; the full catalog, other permissions
and all other product fields remain dependencies. The definition excludes the
name, identifier and source/vendor metadata, while retaining every other field.
Named programs, preparation identities and complete-route verification remain
distinct. This reuses a sequence constraint, not a claim that enzymes have the
same experimental performance.

Screen construction is invocation-owned and checks cooperative cancellation
between frames. It handles at most 32,768 frames and 16 MiB of distinct relation
content; larger requests retain full ordinary navigation. Unsupported or
resource-stopped translations are explicitly unknown candidates, never empty
sets. A single-target request avoids the shared setup. A cold invocation pays
setup again; measure that cost separately from warm navigation. Choose call
allowances that amortize setup: checkpoint transactions still occur per evaluated
step. A cold call can stop during screening before committing a new evaluation.
This change
reduces navigation work per target, so equal evaluation counts are no longer
an equal-work comparison: compare exhausted finite requests, molecular outcomes,
CPU cost and useful preparations. It does not migrate old producer checkpoints.

Survey scheduling retains each examined target's continuation cursor, rather than
its complete latest record. Resume reads every committed step once to restore
proofs, observed classes and progress; only the latest cursor survives that pass.
Full records remain in the checkpoint for replay and retrieval. Each new step
commits before progress is emitted, so a larger invocation budget does not defer
all persistence until the call returns. Measure retained scheduler state and
whole-process memory separately; other admission and proof state still consume memory.

Checkpoint append reads the latest step through the existing `(ordinal, step)`
index, inside the write transaction. It does not recount or scan a target's
growing history for each evaluation. Opening still checks every record and step
for integrity and continuity; append rejects stale steps and exhausted targets.
This adds no cached cursor or schema change. Measure append cost separately from
checkpoint admission and molecular search, including deep single-target histories.

The numerical comparison view validates its cohort once and caches regional edit
distances within the call. Its cache is bounded and cleared on normal exit or
interruption. Small maps retain exact all-pairs fitting. Omitted and explicit
default neighbor settings both use this automatic boundary. Above 2,048 distinct
signatures, the default proposes candidates through compiled molecular neighbor
descent, starting at 64 candidates. Nondefault settings request sparse fitting
above three signatures. Explicit legacy landmark policies remain available, and
captured legacy receipts retain their original policy and canonical bytes. Both paths rerank
with the exact molecular comparison and audit stratified queries against the full
cohort. Retrieval does not assume a triangle inequality. Prepared numeric arrays
and compiled closures are invocation-owned and released after fitting.

Candidate batches and the retained graph use linear storage. Recall below the
declared threshold widens retrieval or raises; it cannot silently publish a lower
quality graph. The receipt reports every audited query, including the minimum
recall. Coverage of molecular search and coverage of the neighbor audit are separate.
NumPy and UMAP remain optional fitting dependencies; viewing frozen coordinates
does not require them. See the [edition guide](../guides/share-atlas-edition.md).

Keep numerical benchmarks in a separate uv project environment when a verification
gate is also running. A normal `uv run` can synchronize away optional atlas
dependencies from a shared environment. For example:

```bash
UV_PROJECT_ENVIRONMENT=.artifacts/atlas-benchmark-env \
  uv run --locked --extra atlas --no-dev python benchmark.py
```

Record the environment and active competing work with timing results. Retain the
small measurement receipts; remove a task-owned temporary environment after its
processes finish. Do not remove shared environments or historical evidence.

Compact atlas capture stores descriptors with the verified authorities and
renders only inspected preparations. It avoids cohort-wide SVG generation;
selected retrieval keeps its authority checks. Ordinary frozen capture preserves
original artwork. Treat opening speed, first drawing latency and storage size as
separate measurements rather than reporting one undifferentiated speedup.

Capturing a released-insert discovery owns one fully admitted read-only survey
reader for the operation. Whole-checkpoint decompression and hash validation run
once; selection admission and complete molecular verification still run per
preparation. The reader closes on success or failure and is never a global cache.
Preservation selections retain their existing retrieval path and extra reports.
Explicit recorded-source capture also checks complete input bindings before and
after export, with generator and exporter provenance kept separate.

An open compact edition admits its descriptor models once. Each later access
still reads and checks the descriptor file against its manifest; selected views
still compare the descriptor with the complete authority. Returned models detach
mutable dictionaries from the retained index. This memory belongs to the edition
instance and is released with it, separately from browser file-cache limits.

Edition selection retains a small immutable index of coordinate rows, keyed by
preparation identity. It avoids decoding unrelated preparations when selecting
one molecule, preserves every row for repeated identities, and retains the full
regional-preservation proof path. Saved-view validation uses this admitted
membership rather than calculating facet statistics. Selected authorities and
landscape bytes still undergo their checks on access. Account for this index
separately from descriptor and drawing caches when measuring resident memory.

Browser inspection generates the active landscape, its linked parameter trace
and distributions. Inactive drawings are deferred until selected. Presentation
or query changes can invalidate this bounded drawing group; selection and camera
changes do not. Hover supplies one exact trace over the retained axes, using the
same full-cohort parameter values as the publication SVG. The public preview
packet still includes its complete trace drawing. Closing
the inspection removes its owned drawing files and clears cache accounting.
Compact inspection derives family counts and distributions once from its admitted
query answer. Its transport dictionaries reuse scalar keys without serializing
each repeated word or count; numeric, boolean and string values remain distinct.
These are internal projections. Public query results and figure exports retain
their existing contracts.

The shared renderers have explicit publication and inspector composition profiles.
The inspector uses a narrower axis grid and larger molecular annotations; both
profiles retain exact base addresses, measured parameter anchors and full paths.
Axes, trace coordinates and feature connectors share one profile. Its contents
bind projection and cache identities, so mismatched geometry cannot be reused.
Axis bands measure heading rows and value contours before placing their shared
numeric and categorical range. Static paths and preview overlays consume that
same layout; larger type cannot reuse fixed heading or band offsets. Filtering
does not change these coordinates. The profile declares whether teaching slots
must stay stable, independently of its typography.
Curated static figures fit the complete measured teaching content, including
primer contours and attached labels. Interactive figures retain their stable
viewports and teaching slots. Both use the same nucleotide coordinates and
feature anchors; fitting a static frame does not recompute molecular geometry.
The main parameter landscape retains its publication composition. Its inspector
axes are loaded once per cohort, not regenerated on each hover or pin.
Static node labels and hover labels share wrapping and contour dimensions, which
also bind the trace projection identity. Hover temporarily hides only intersecting
background label paint; node marks and keyboard targets remain mounted. Preparing
another preview does not change the current scene. Clearing, replacing or closing
inspection restores the prior label visibility. Label bounds are read from the
SVG's recorded geometry rather than measuring layout on each pointer movement.

The inspector's edge supports pointer and keyboard resizing. It keeps the visible
molecular scene anchored and reserves map space; figure focus and compact windows
hide that control. Resizing updates layout in animation frames without changing
the inspection receipt or requesting new molecular artwork. Close disconnects
its observers and releases pointer capture. Measure this local operation apart
from loading newly visible route scenes.

Current-style previews use the same inspector glyph profile when pinned or
hovered. Captured artwork stays unchanged unless current style is requested;
unsupported captured schemas retain their original artwork in either path.
When the user has scrolled past the teaching molecule into the route, the private
preview request includes only the visible scene phases. Compact editions validate
one authority and share its projection across the hairpin and those scenes. Both
are prepared before the browser commits the replacement. While the teaching
molecule is visible, its faster preview path remains independent of scene loading.
The previous preparation stays gray and inactive until the matching replacement
is ready. This adds no waiting period, persistent authority cache or streaming
connection. Scene drawings share the existing bounded hover cache and are removed
with it; captured editions retain their original scene artwork and provenance.
The browser's private packet is composed before its manifest is written. Public
figure exports and material retrieval retain their existing defaults.
Private molecule packets draw the inspector composition directly and record that
profile. The inspector reuses a matching composition instead of first drawing a
publication overview and replacing it. Captured artwork keeps its original profile;
requesting current style recomposes it explicitly. Live saved-view validation still
performs its native replay independently of this presentation optimization.

Use an isolated headless browser for repeated automated interaction checks, and
reuse an installed browser rather than downloading one during the check. Explicit
download tests use an owned temporary download directory and wait for the browser's
completion event before teardown. Hover, selection and figure navigation must not
start downloads. Close the owned browser and remove its profile and downloads;
leave the operator's regular browser and files untouched. Visible review windows
are for deliberate visual inspection, not routine test iteration.

Dense similarity maps use two canvas layers: a retained cloud and a selected-point
overlay. A compact index shares its exact positions with the SVG exporter. A
spatial index supplies pointer picking; an active accessible option supplies
keyboard navigation without one DOM node per preparation. Public SVG exports
remain vector artwork. Resizing or changing the camera repaints the cloud;
hovering repaints only the highlight. Pixel density is capped at two. Closing
releases both drawing layers, the spatial index and event observers.

Molecular color views reuse the admitted parameter rows. End-gap and loop-size
scales include the entire recorded edition, so filtering does not change their
meaning. Exact sticky-end words are highlighted on the chosen side; unavailable
measurements remain distinct from zero. Recoloring repaints the cloud locally,
without a request, query change or coordinate fit. Eligibility and selection use
separate hollow marks and outlines.

The local browser transport sends cohort facts once per query. Later responses
may omit them only when the client names the matching cohort digest. This is a
transfer optimization: action tokens, selection checks and authority reads still
apply. Dependent panels immediately disable superseded content while retaining their
bounds and scroll position. A previous molecular drawing is shown only as a labelled,
subdued reference. Hairpin and trace adopt the new preparation together after their exact
identities agree. Local loading indicators have no minimum display
time, add no network work, and respect reduced-motion preferences. A route or
material handoff that has not been requested uses a pin prompt rather than a
spinner. Failed loads stay explicitly unavailable; retry uses the saved response
without repeating the selection action. Closing the inspector during a pending
selection does not reopen it when that selection finishes.

The inspection summary commits with the matching molecule and trace. Its brief
comparison uses canonical parameter changes, so equivalent measurements appear
once; it does not assert that surroundings are preserved. Filtering may exclude
the pinned preparation while retaining its drawing as an inspection reference.
Hover keeps that reference explicit. Construction cost comes from the same
already-projected atlas, names the measured endpoint, and adds no retrieval or
route-render request. Escape restores a transient preview before leaving figure
focus or closing the inspector.
Returning to the already-inspected point restores its existing drawing immediately,
without another preview request or loading indicator.

Compact hairpin previews reuse the inspector's admitted query context instead of
rebuilding the cohort and selecting a preparation again. The snapshot must match;
the selected authority bytes and molecular descriptor are still checked afresh.
Public preview packets and handoffs retain their existing contracts. This removes
repeated cohort work, not the exact molecular projection or its checks.

View validation derives state IDs from the verified route rather than projecting
the teaching figure. Receipt creation admits its landscape once within that call;
the next call reads and verifies the current bytes again. Neither optimization
retains a mutable molecular model as a process-wide authority cache.

## Choose the verification boundary

Test categories describe the responsibility being protected. Test count alone
does not describe coverage of molecular sequence space.

| Responsibility | Question answered | Typical evidence |
| --- | --- | --- |
| Molecular rules and contracts | Are bases, cuts, pairing, chemistry, coordinates and identities correct? | Unit/property/contract checks, including invalid and contradictory inputs. |
| Workflows and trust boundaries | Does the same request reach a complete, portable preparation, and does altered saved evidence fail? | Discovery, continuation, CLI/API selection, retrieval and fresh admission/replay. |
| Presentation | Does the view faithfully show the recorded molecule and keep the user's selection? | Projection contracts, SVG/PDF inventories, layout, exact bases and browser interaction checks. |
| Repository integrity | Are modules, documentation, dependencies and public boundaries coherent? | Strict preflight, lint, types, documentation and privacy checks. |
| Distribution | Does the built and installed utility contain the required assets and reproduce its public behavior? | Clean installation and source/wheel comparisons. |

These are responsibilities, not new folders. Existing tests stay with their
owners. The presentation selection lives in `scripts/verification_tests.py`;
extend it when a new view responsibility is introduced. It refuses stale or empty
selections. The complete source gate still collects every test.

```bash
bash scripts/agent-verify --scope presentation
bash scripts/agent-verify --scope source --workers 2
bash scripts/agent-verify --workers 2 --distribution routine
bash scripts/agent-verify --workers 2  # extended distribution qualification
# Match hosted coverage on a machine with four available cores:
UV_PYTHON=3.14 COVERAGE_CORE=sysmon bash scripts/agent-verify --workers 4
```

Choose one command for the task; do not run these gates in sequence.

- **Repository-only maintenance:** for documentation and repository checks when
  runtime source, packaged assets, dependencies, build rules and verification
  routing are unchanged. Run strict preflight, the affected checker regression
  tests and lint on changed files. Run the checker against the real repository
  as well as its rejection examples. Record this as focused repository
  verification, not a source or distribution gate. Changes to verification
  routing follow the runner rule below; changes to installed behavior use the
  appropriate scope below.
- **Presentation:** for rendering, molecular projection, typography, layout and
  browser-only changes. Run the changed view's positive and negative checks,
  visually inspect the actual export, and verify that its molecular inventory
  is conserved. This scope runs the declared view tests, every browser-model
  check, strict preflight, lint and type checks. It does not assert whole-source
  coverage or installed-package equivalence.
  Deriving new molecular facts, changing coordinate meaning or altering product
  identity requires source verification even if the result appears in a plot.
- **Source:** for models, molecular rules, request interpretation, search,
  persistence, identity, admission or handoff changes. It runs the entire Python
  suite with the existing 90% coverage floor, all browser checks and repository
  checks. Uncertain change impact also requires the full gate below.
- **Full:** source verification plus dependency audit and installed-distribution
  verification. `--distribution routine` builds and scans the wheel/sdist,
  compares every packaged source/asset byte with the checkout, installs only
  runtime dependencies in an isolated environment, and exercises discovery,
  reopening, a complete preparation, exact API/CLI oligos and PDF/SVG output.
  It reuses the existing public example. `--distribution extended` (the default)
  retains the complete source/wheel workflow comparisons. Use extended for
  packaging, dependencies, CLI wiring, asset inclusion, verification changes,
  releases or uncertain impact. CI selects the mode below. A manuscript-only
  change in a consumer repository uses that owner's checks.

The routine installation emits stage names, elapsed times and separate logs into
one create-only directory below `.artifacts/verification/`. Each stage has a
five-minute deadline; failure or timeout stops qualification and cleans its
process group. Successful temporary environments and molecular outputs are
removed. The small gate took about 44 seconds locally with cached dependencies;
this is not a full-suite timing or a hosted performance guarantee. The source
suite remains the larger cost.

The extended runner labels its workflow groups and reports elapsed time and the
failed group. Its expensive parity cases run only in extended mode. We keep
those reference executions self-contained rather than introducing cross-run
pytest evidence caches; small archive/asset assertions and the public design
case are shared by both modes. No scientific source tests were removed.

Verification-runner changes need the routing/failure tests in
`tests/repo/test_verification_scopes.py` and the affected real scope. A stubbed
runner test proves command selection and failure propagation, not molecular
behavior. A narrowed scope must be named in the handoff; it must not be reported
as a full gate.

### Hosted CI policy

Pull requests run the complete source suite on Python 3.14 with branch coverage,
using coverage.py's lower-overhead `sys.monitoring` core. The 90% floor and test
membership are unchanged. Python 3.12 and 3.13 remain supported;
their contract and integration suites run through the separate
`python-compatibility.yaml` workflow on explicit dispatch and during release.
Release publication depends on both compatibility and exact-distribution checks.
Dispatch compatibility for changes that may break an older interpreter. The
repository's local Python default and minimum requirement remain 3.12; the command
above selects the faster coverage runtime without changing a deployed runtime.

Main requires an up-to-date pull request with successful `Checks`, dependency
review and CodeQL, including for administrators. CI therefore does not repeat
the full suite on the subsequent squash-merge push. Manual dispatch remains a
complete verification path. This relies on those branch protections: restore
push verification before permitting direct or unchecked main updates. Release
still qualifies its exact wheel/sdist and supported Python versions. Coverage
reports come from PR qualification; there is no separate post-merge report.

The coverage choice was measured on one exhaustive-completion/replay test using
three alternating fresh-process trials per condition (macOS arm64,
coverage.py 7.15.4, the same locked dependencies):

| Runtime and coverage core | Median wall time | Trial range |
| --- | --- | --- |
| Python 3.12.11, CTracer | 95.10 s | 91.14–96.62 s |
| Python 3.14.7, CTracer | 104.03 s | 100.95–110.11 s |
| Python 3.14.7, SysMonitor | 66.45 s | 64.70–68.04 s |

All nine trials passed the same scientific assertions. Python 3.14's two cores
recorded identical executed/missing line and branch sets in every trial; changing
the interpreter alone was slower. The adopted combination reduced this sample's
time by 30.1%, not a claimed full-suite speedup. The node is
`tests/integration/test_survey_completion_execution.py::test_public_completion_matches_exhaustive_product_choices_with_fewer_attempts`;
run it with `--cov=hop_design --cov-branch --cov-report=json` and the declared
`COVERAGE_CORE`. A subset benchmark needs `--cov-fail-under=0`; the full gate
retains 90%. Coverage.py documents the
[core selection and Python requirements](https://coverage.readthedocs.io/en/7.15.4/config.html#run-core).

`scripts/ci_scope.py` limits the smaller merge gate to its exact README/banner
path allowlist. It checks the complete changed-path set, including both sides of
renames. Empty, mixed, unknown, or unavailable comparisons require the full gate;
invalid revisions or a failed diff stop verification. For full verification,
ordinary Python source, tests and Markdown guides use routine installation.
Packaging/dependencies, CLI entry points, browser assets, scripts, workflows,
examples, unknown paths or missing comparison evidence use extended installation.
Mixed changes take the stronger mode. Manual CI always uses extended. Both
outputs are checked before execution; a missing mode fails. The selector itself
therefore receives extended qualification before this policy can be merged.

The README/artwork gate runs strict preflight, repository lint and workflow
validation, CI contract tests, distribution builds and metadata checks. Review
the banner visually as well. This gate establishes repository and packaging
integrity, not molecular replay or installed-package parity. Packaged browser
assets and molecular figures do not qualify for this exception.

The stable `Checks` job remains required for both scopes and rejects a failed,
canceled or skipped verification job. The workflow itself is never path-skipped;
that would leave required checks pending. The full gate still produces coverage;
artwork-only runs do not upload or replace that report.

### Use bounded parallelism

`--workers 2` or `--workers 4` runs a bounded number of Python worker processes
with `loadscope`; the default is serial. This keeps module/class fixture groups
together and avoids unbounded CPU/memory expansion. A session fixture is still
instantiated in each worker that needs it. Hosted CI uses four workers on the
public Ubuntu runner's four CPUs and 16 GB RAM; local callers choose a smaller
count when sharing the machine. Compare identical test membership and record
wall time and process-tree memory before increasing concurrency.
[GitHub runner specifications](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[pytest-xdist distribution](https://pytest-xdist.readthedocs.io/en/stable/distribution.html)
and [fixture lifetime](https://pytest-xdist.readthedocs.io/en/stable/how-to.html#making-session-scoped-fixtures-execute-only-once)
describe that behavior. Coverage from workers is combined by
[pytest-cov](https://pytest-cov.readthedocs.io/en/stable/xdist.html).

Both source and presentation runs save JUnit timings in `.artifacts/verification/`
and print their slowest tests. Every gate stage reports its start, duration and
exit status in the log and `stages.tsv`, retained by CI even on failure. Strict
preflight checks API exports and CI/documentation contracts before the expensive
source suite. Lint and formatting run once through the repository hooks.
The full gate audits hashed locked requirements, including development and
optional dependencies, before scientific tests. This catches dependency failures
early instead of running the source suite first. The isolated installation still
contains only the declared runtime dependencies.
Compare setup with call cost: constructing a broad
fixture is different from repeatedly reopening its authorities. Profile a slow
case with `python -m cProfile -o ... -m pytest path::test` and measure ordinary
timings separately. CPU-bound replay should be addressed before adding more
workers or weakening admission. Do not start duplicate gates; a failed scope
remains failed until repaired and verified.

An October 2026 local pilot used three fresh-process trials per worker count,
identical test membership and `loadscope` on Python 3.12/macOS arm64:

| Workload | Serial median | Two-worker median | Peak summed process RSS, serial → two workers |
| --- | --- | --- | --- |
| 19 atlas, inspection and print checks | 27.14 s | 24.00 s | 339 → 651 MB |
| Two discovery/retrieval/replay checks | 30.78 s | 20.90 s | 254 → 483 MB |

Two workers helped these samples but nearly doubled their memory footprint.
These timings do not predict a full-suite speedup: shared session fixtures are
repeated across workers, and module groups may have unequal costs. Serial remains
the portable default; two workers are an explicit option. Summed RSS includes
shared pages and is not a measurement of unique physical memory. Retain the
commands, individual trial results and environment with a performance review.

A separate November 2026 pilot compared two and four workers on four discovery,
checkpoint upgrade/resume and CLI/API handoff tests (Python 3.14.7/SysMonitor,
macOS arm64, three alternating trials, unchanged `loadscope` grouping):

| Workers | Median wall time (range) | Median child CPU time | Maximum summed process RSS |
| --- | --- | --- | --- |
| 2 | 16.98 s (15.33–17.74) | 23.31 s | 602 MiB |
| 4 | 13.34 s (12.19–15.58) | 26.50 s | 996 MiB |

All 24 test executions passed; test membership and line/branch coverage matched.
Four workers reduced sample latency by 21.4% while using 13.7% more CPU time and
more memory. This is a latency choice within the hosted runner's capacity, not
an efficiency claim or a prediction for the full Linux suite. Local serial/two
worker options remain available.

Use small real constructions for corruption and boundary tests. Keep broad
populations for coverage, diversity and grouping tests. The shared read-only
GAAA/TTTC fixture serves query and projection tests; tests that mutate files copy
it first, and admission tests load it afresh. Share immutable setup, not acceptance
decisions between independent tests.

Pytest removes successful temporary test directories and retains three failed
sessions. `wheel-smoke` owns and removes its temporary environment. Keep profiles,
logs and reproducing inputs separate from generated preparations. Before removing
any older outputs, check their owner and reproduction role; age alone is not a
cleanup rule. Benchmark cleanup tests cover both errors and interruption.
