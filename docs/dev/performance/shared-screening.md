# Shared constraint screening

Use this reference when a profile points to necessary end-pair projection or
navigation across targets. Screening shares necessary constraints; complete
construction remains a separate calculation.

## Traverse bounded basal work

Necessary end-pair screening traverses basal work once within its retained-DNA
bound, rather than rescanning the target roster at every possible overhead
level. Canonical offsets and the fixed pairing length make the retained overhead
monotone. The stream preserves the units and order of the explicit level-by-level
traversal and stops at the first offset above the bound. Individual-level callers
keep their existing behavior; no search permission or resource ceiling changes.

## Project contact assignments

Initialize exposed positions with their placed base masks, complementing each
mask when the output observes the opposite orientation. A variable observed
once needs no separate unary factor. Repeated observations still share an exact
assignment factor, so copies and complements remain correlated. Contact factors
and their combined noncanonical allowance are applied afterward.

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

## Reuse across lengths and local domains

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

Identical projected problems can also recur across local domains. One discovery
invocation retains at most 512 exact projected sets and 8 MiB of serialized
values. Bounded keys and Python object overhead consume additional memory. The
key snapshots the placed masks, exposed copies and complements, contact
positions and permissions, output length and noncanonical allowance. A hit
imports the immutable set into the current builder, enforcing that builder's
decision and operation limits. Failed or unfinished calculations are never
retained. Full placement and enzyme checks still precede projection; complete
preparations still pass ordinary compilation. Eviction recomputes the same set.

## Bound the frame index

The invocation-owned basal-frame index retains at most 32,768 established
relations and 16 MiB of canonical relation content; Python object overhead is
additional. This allows a recurring placement set to survive between requested
end pairs instead of being evicted on every sweep. Target membership is checked
on each access, unsupported translations are not reusable rejection facts, and
the request and sequence limits remain bound to the index. Entry or byte pressure
evicts the least recently used frame without changing its answer. Nothing persists
between invocations. Measure cold construction, repeated access and whole-process
memory separately; a cache-hit improvement does not establish campaign throughput.

## Share navigation across targets

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

## Reuse equivalent enzyme definitions

Named release enzymes with identical modeled definitions can also share a
necessary relation through the existing bounded cache. Both basal and release
permissions must explicitly select the same allowed singleton before lookup.
Only its two role references are normalized; the full catalog, other permissions
and all other product fields remain dependencies. The definition excludes the
name, identifier and source/vendor metadata, while retaining every other field.
Named programs, preparation identities and complete-route verification remain
distinct. Reuse applies only to the sequence constraint.

The scratch relation key hashes a fresh typed JSON snapshot of the full catalog,
including entry order, metadata and every recognition/cut definition. This
avoids constructing its nested Python dictionary for each placement. No catalog
object or file metadata substitutes for reading its current content. Public
canonical serialization, molecular identities and saved records are unchanged.

## Cancellation and measurement

The screen is built once per discovery call and checks cooperative cancellation
between frames. It handles at most 32,768 frames and 16 MiB of distinct relation
content; larger requests retain full ordinary navigation. Unsupported or
resource-stopped translations are explicitly unknown candidates, never empty
sets. A single-target request avoids the shared setup. A cold invocation pays
setup again; measure that cost separately from warm navigation. Allow enough
evaluations per call to measure whether setup costs outweigh the navigation
savings. Checkpoint transactions still occur per evaluated step. A cold call can
stop during screening before committing a new evaluation. This change reduces
navigation work per target, so equal evaluation counts are no longer
an equal-work comparison: compare exhausted finite requests, molecular outcomes,
CPU cost and useful preparations. It does not migrate old producer checkpoints.
