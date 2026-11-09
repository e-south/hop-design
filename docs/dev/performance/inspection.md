# Browser inspection

Pinning a molecule projects its exact states, comparison and construction cost,
but draws only the hairpin overview. Opening the route draws its processing
states. Both views use the same admitted records and bounded preview cache;
closing the inspection server removes its temporary files. Public `atlas()` and CLI
atlas exports still produce the complete route. Measure pinning and opening the
route separately: deferring artwork does not remove molecular verification.

## Hover and selection

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

## Draw only visible route scenes

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

## Isolate compact preview rendering

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
browser-only changes still use the
[presentation boundary](verification.md#choose-the-verification-boundary).

## Rank molecular neighbors

Neighbor inspection ranks eligible descriptors with the prepared exact-distance
kernel and reconstructs preservation facts only for its returned membership plus
the reference. The browser first requests ranking without control verification;
the deliberate control action uses the same API with verification enabled.
Neighbor computation runs outside the session lock. Request identities prevent a
late cancellation from stopping newer work, and selection changes or teardown
cancel the current request. Deadline and cancellation checks occur between ranking
steps and major phases; they do not interrupt a molecular validator mid-call.

## Inspector rendering and interaction

Full-route previews retain at most four packets and 128 MiB of files; plot artifacts
use a separate four-entry, 16-MiB cache. The browser loads the visible molecular
view and keeps a six-entry, 8-MiB artifact cache. Closing the server removes its
temporary previews and plots. Lightweight teaching previews and visible route
scenes each retain up to 12 entries within one shared 8-MiB file budget. They
never generate the complete route or a PDF.
Requested material downloads remain in
the inspection output directory. Multipage print figures are generated on export,
not on every selection.


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

### Composition and label geometry

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

### Resize without redrawing molecular content

The inspector's edge supports pointer and keyboard resizing. It keeps the visible
molecular scene anchored and reserves map space; figure focus and compact windows
hide that control. Resizing updates layout in animation frames without changing
the inspection receipt or requesting new molecular artwork. Close disconnects
its observers and releases pointer capture. Measure this local operation apart
from loading newly visible route scenes.

### Commit current-style previews

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

### Check interactions in an owned browser

Use an isolated headless browser for repeated automated interaction checks, and
reuse an installed browser rather than downloading one during the check. Explicit
download tests use an owned temporary download directory and wait for the browser's
completion event before teardown. Hover, selection and figure navigation must not
start downloads. Close the owned browser and remove its profile and downloads;
leave the operator's regular browser and files untouched. Visible review windows
are for deliberate visual inspection, not routine test iteration.

### Draw dense maps

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

### Transport and commit matching results

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
