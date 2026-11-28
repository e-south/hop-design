# Measure browser interaction

Use this page to separate hover, selection and loading feedback from drawing time.
Return to [browser inspection](../inspection.md) for the rendering and cohort guides.

## Hover and selection

Hover keeps one active preview and only the latest waiting choice. Leaving the
map, selecting a preparation or closing the page discards waiting previews;
already-running server work can finish but cannot replace the current view.
Crossing empty space within the map retains the last inspected preparation.
Inspection starts immediately through that bounded controller; a second debounce
timer must not add latency before a point can be inspected. Rapid target changes
replace waiting work instead of growing a request queue.
Clearing the browser artifact cache also invalidates pending cache admissions.
Measure server work and retained browser memory separately from stale-display
protection.

Loading preserves the last coherent drawing and layout. The molecule becomes
muted and inert while its replacement loads; parameter-trace controls remain
interactive. Progress uses the fixed inspector heading rather than cards over
the molecule or X. Errors remain visible at the affected panel. Existing drawing
nodes are reused without extra rendering, cloning or requests.
Pinning freezes the displayed preview until the committed drawing is ready,
including the first pin when there is no previous selection. Leaving a point while
that mutation is pending cannot clear the reference or expose an unfinished result.
The hairpin, exact trace and difference explanation commit together; route and
material panels cannot present another preparation as current. Loading adds no
request, timer or minimum display duration. Cached inspection can appear immediately.
The trace is parsed before this commit; its drawing adapter mounts the same
validated tree rather than parsing it again.
Measure loading feedback separately from time to usable content.
If a combined preview fails, visible route slots enter the same explicit error
state instead of remaining in preparation. A stale failure cannot replace the
loading state of a newer preview. The retained drawings remain non-interactive.

Both map canvas renderers repaint retained points after context restoration. They
coalesce restoration into one animation frame and remove their listeners on
teardown. Recovery neither reloads the cohort nor changes the camera or selection;
ordinary hover still repaints only the selection layer.

## Resize without redrawing molecular content

The inspector's edge supports pointer and keyboard resizing. It keeps the visible
molecular scene anchored and reserves map space; figure focus and compact windows
hide that control. Resizing updates layout in animation frames without changing
the inspection receipt or requesting new molecular artwork. Close disconnects
its observers and releases pointer capture. Measure this local operation apart
from loading newly visible route scenes.

## Check interactions in an owned browser

Use an isolated headless browser for repeated automated interaction checks, and
reuse an installed browser rather than downloading one during the check. Explicit
download tests use an owned temporary download directory and wait for the browser's
completion event before teardown. Hover, selection and figure navigation must not
start downloads. Close the owned browser and remove its profile and downloads;
leave the operator's regular browser and files untouched. Visible review windows
are for deliberate visual inspection, not routine test iteration.

## Transport and commit matching results

The local browser transport sends cohort facts once per query. Later responses
may omit them only when the client names the matching cohort digest. This is a
transfer optimization: action tokens, selection checks and authority reads still
apply. Dependent panels immediately disable superseded content while retaining their
bounds and scroll position. The previous molecule stays subdued while the
parameter controls remain available. Hairpin and trace adopt the new preparation together after their exact
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

Complete preparation uses one compact loading cue in the fixed inspector heading
for visible pending steps. Individual scene slots keep their phase labels and measured bounds,
without repeated loading cards or screen-reader announcements. Retained drawings
remain subdued and inactive while updating. Failures and unavailable states still
show and announce their specific notice at the affected step. Offscreen steps do
not imply ongoing work; the cue clears on completion, failure, restoration or close.

The optional atlas X explanation decodes only the inspected member from the
already-loaded comparison packet. It adds no requests or fitting work, and stays
closed until requested. Its content commits with the matching hairpin and X;
Escape closes it before changing the inspector. Atlas options stay within the
plotting area, below its legend in narrow windows. Expanded controls scroll
inside that area and leave the X row visible in short windows. They retain alternate
population views and saved-view loading; Fit atlas resets the existing camera.
The color legend and feature explanation occupy the left of the atlas. Numeric
X meanings and arithmetic are defined in [molecular comparison](../../../reference/molecular-comparison.md).

The hover wrapper is transparent: FigureLayout already removes SVG page backgrounds
and hides the prior molecule before showing a preview. Its link layer can therefore
remain behind molecular ink without an opaque rectangle masking the molecular
origin. Highlighted links use a quiet translucent fill, with no decorative shadow.
