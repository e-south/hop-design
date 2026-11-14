# Measure inspection rendering

Use this page for scene drawing, worker startup, cache limits and composition.
Return to [browser inspection](../inspection.md) for interaction and cohort behavior.

## Draw only visible route scenes

The private scene-inspection endpoint accepts distinct names from the finite
recorded phase vocabulary, for one preparation. The browser submits the visible
scenes together so they share one molecular admission and projection. An absent
or ambiguous phase is explicitly unavailable. Only requested scenes are drawn,
while label introduction and incoming-material placement retain the whole route's
context. Measure authority access, scene drawing and cache reuse separately.
For an isolated linear/early scene request, skip the folded-frame headroom prepass.
Full-route and mixed/folded requests retain their shared measurement pass. Exact
SVG bytes and scene metadata must agree with the corresponding full projection;
a performance change cannot bypass molecular admission or change input placement.
Scene composition keeps a native element tree through annotation, measurement
and placement. Serialization occurs at the export boundary, avoiding a second
document representation and a serialize/reparse cycle for each route scene.
The same molecular glyphs and addresses serve standalone and composed drawings.
After pinning, scrolling loads only visible scenes. Hover reuses those fixed
phase slots and identifies prior drawings immediately. While the teaching molecule
is visible, scene loading waits for the matching hairpin. When scrolled into the
route, a combined preview prepares the hairpin and visible phases before committing
them together. No additional authority cache is retained.
The scene channel permits one active request and one latest pending request.
Leaving restores up to four cached pinned scene nodes; offscreen drawings are
detached. Changing route presentation anchors scroll to the inspected phase or
its nearest surviving neighbor. The full figure remains an explicit focus action.

Each new derivation reads the admitted authority; a cache hit reuses already-admitted
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

The worker accepts one active job, with a ten-second default deadline and no
internal queue. A private pipe avoids
process-pool cleanup locks after a crash. A timeout or failed process discards that
process and pipe; an explicit retry starts a fresh renderer. Closing the session
stops rendering before waiting for the session lock, then removes temporary files.
Shutdown allows one second after terminate and one second after kill. There is no
silent fallback or alternate molecular authority. Measure cold process startup,
warm cache misses, parent-plus-child CPU and memory separately. Combined hover
requests include their visible route phases in this worker.
Separate `/api/scenes` requests remain synchronous.

The console entrypoint defers CLI registration until invoked. Its standard
`__main__` module stays under the CLI dependency rules. The detached pipe target
is colocated with the existing preview job and exposed through the inspection
facade; the command adapter still owns process startup, deadlines and disposal.
Spawned renderers must not import command registration. Benchmark the installed
console command as well as a guarded Python caller: spawn re-executes the launch
script, and bytecode-cache differences can reverse an apparent startup gain.
No extra process, prewarming, admission cache or fallback is introduced.

`test_inspection_worker.py` checks failure, timeout, concurrent work and teardown.
`test_isolated_preview.py` compares exact drawings and summaries and rejects altered
authority. Changes to that extraction/admission boundary require source verification;
browser-only changes still use the
[presentation boundary](../verification.md#choose-the-verification-boundary).

## Cache and export limits

Full-route previews retain at most four packets and 128 MiB of files; plot artifacts
use a separate four-entry, 16-MiB cache. The browser loads the visible molecular
view and keeps a six-entry, 8-MiB artifact cache. Closing the server removes its
temporary previews and plots. Lightweight teaching previews and visible route
scenes each retain up to 12 entries within one shared 8-MiB file budget. They
never generate the complete route or a PDF.
Separate entry quotas keep scenes from evicting a small teaching working set;
byte pressure still evicts the oldest artifact across both.
Requested material downloads remain in
the inspection output directory. Multipage print figures are generated on export,
not on every selection.

## Composition and label geometry

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

## Commit current-style previews

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
Compact pinning passes its already-typed molecular atlas to the same teaching
renderer used by preview. It does not serialize that generated atlas and validate
it again merely to draw the overview. Archive/snapshot admission, descriptor
validation, reference comparison and saved-view validation still run at their
existing boundaries. Verify exact overview bytes and complete summary parity,
including the inspector profile, before accepting a timing change.
Private molecule packets draw the inspector composition directly and record that
profile. The inspector reuses a matching composition instead of first drawing a
publication overview and replacing it. Captured artwork keeps its original profile;
requesting current style recomposes it explicitly. Live saved-view validation still
performs its native replay independently of this presentation optimization.

## Rendering and route policies

Renderer version and route composition are separate API and saved-view choices:
`render_policy` selects captured or current glyphs, and `presentation.route`
selects `complete` or `assembly`. The current browser has no Renderer or route-policy
selector. **Full figure** opens the route; it does not change either policy.

Captured artwork cannot be recomposed, while compact editions draw their recorded
molecular authority on demand. A recorded preference can therefore use current
glyphs when no artwork was captured; the rendering receipt states this explicitly.
Both route profiles retain the complete molecular record and use the same
processing renderers as API and CLI exports. Assembly groups cleanup operations
without removing their recorded states or transition identities.
