# HOP Design reliability contract

## Determinism

The same normalized spec, compiler version, locked catalog/profile references,
and route must produce byte-identical artifacts, plan digest, manifest digest,
plan ID, and bundle ID. Canonical JSON is UTF-8, key-sorted, compact, and ends
with one newline. FASTA uses deterministic headers, 80-column sequence lines,
and one trailing newline. Host paths, timestamps, usernames, and environment
ordering do not enter content identity.

Product-to-construction lowering reuses the request's immutable characterized
catalog when binding foldback, basal and release permissions. It validates the
newly derived geometry and complete route through their normal models. This is
object reuse within a translation, not a persistent admission cache; external
JSON and saved-bundle admission still validate their complete contents.

## Bundle integrity

New complete-route states, programs, source preparations and materialized
realizations generate their content identities in the normal validation pass.
The private creation context is bound to one model type and identity field,
consumed by one root object and discarded when creation finishes. Nested records
still verify their supplied identities, and all schema, molecular, lineage and
route checks still run. Independent model/file admission always checks the
supplied identity. This removes duplicate serialization during creation without
retaining validation authority or adding a caller option to disable checks.

Survey checkpoints remain bound to their exact producer. Ordinary resume and
verification never accept another producer. An explicit `survey upgrade` replays
every saved evaluation into a new checkpoint under the current producer. Results,
continuations, exclusion scope and molecular authorities must match; only
regenerated exclusion certificates may change their producer digest and resulting
references. The original checkpoint remains unchanged. The transition receipt
binds both producers and checkpoint hashes. It establishes replay equivalence of
the saved prefix, not universal compatibility or validity of unseen results.
Writers must be stopped during this operation. Failed or interrupted upgrades
publish no destination; resume the preserved original with its original runtime.

`hop-bundle.json` inventories every content artifact except itself. Each entry
records a normalized relative path, media type, byte count, and SHA-256 digest.
Verification rejects missing, symlinked, modified, unmanifested, path-traversing,
or root-digest-inconsistent content. It also loads the strict spec, plan, and
provenance schemas; checks their identities and locked references against each
other; then deterministically recompiles the spec and requires the complete
plan, artifact set, and manifest to match. This replay catches a consistently
resealed bundle whose authored intent and derived state disagree. Writes use a
sibling temporary directory, verify it, then rename it atomically. Existing
output paths are never replaced.

`method-bundle.json` applies the same safe-path, complete-inventory, digest,
atomic-write, and no-overwrite rules to a method request and plan. Verification
parses both strict schemas, recompiles the request, and requires the plan,
trajectory, FASTA, GenBank, artifact inventory, manifest digest, and bundle ID
to match byte for byte. A checksum-valid reseal of one generated artifact is
therefore rejected.

`construction-bundle.json` inventories one exact complete-construction result
and every byte of the separately verified design bundle embedded below
`authorities/design/`. Verification checks the root result and manifest
digests, construction and design identities, exact artifact inventory, and
safe paths. It then semantically replays the design authority, each embedded
foldback and optional basal authority, whole-route composition, reaction-site
assessment, endpoint products, disposition accounting, rejection reasons, and
grouping. Finally, it recompiles the expected construction bundle and requires
exact artifact and manifest equality. Construction-bundle and projection
writes are atomic and create-only.

Within request execution, outcome and trajectory projections reuse the immutable
compilation receipt after its construction-bundle write passes full staged-file
verification. They do not reload that just-published directory. This reuse is
limited to the invocation that compiled the authority; every independently loaded
bundle still undergoes the complete checks above. A failed write returns no
execution handoff. No process-wide or path-based verification cache is used.

Fresh complete discovery admits the exact result produced by its composer after
verified upstream authorities and strict result validation. It does not rerun
that same composer immediately. The result validators still check identities,
route derivation, material lineage, endpoint evidence and disposition accounting.
Only this internally generated result receives direct admission; there is no
caller-supplied result or verification-disable option on that path. Admission
binds the receipt object's identity and current canonical result digest, so
copying a container or altering its content cannot inherit that authority.

Source compilation packages this admitted result. Explicit result verification,
independently constructed result receipts, bundle compilation and staged-file
publication still perform complete replay. Independently loaded files retain all
checks above. Scaffold discovery projects branch facts from candidate
receipts already admitted during the same invocation; the projection layer has
no optional bundle-admission path. Candidate publication and file admission remain
separate checks. Reopening a saved discovery replays its candidates afresh.
Identical local foldback/basal proof inputs may reuse a successful replay within
one saved-discovery admission or one bounded options evaluation. Each reuse
reparses the strict model and compares the full
canonical result bytes, including request, catalog and limits, under the current
producer identity and replay policy. The scope retains at most 64 proofs and
8 MiB, ends when that call returns or raises, and never bypasses file checks,
complete-route replay or projection comparison. Failed proofs are not retained.
A separate load or evaluation starts a new proof scope. Candidate quotas,
enumeration order and completeness accounting do not depend on cache warmth.


Comparison retrieval admits its captured discovery pool once, checks the saved
assessment against that pool, and retrieves the explicit selection inside the
same capture scope. Assessment and retrieval share those verified receipts;
another public call captures and admits its input again. Membership, reference,
material-reuse and selected-preparation checks remain unchanged.
Selected-set assembly binds each saved selection to its admitted result and
accepted realization before projecting or copying the immutable artifacts. It
does not reread those authorities within the same capture. Standalone set requests
still load and replay every referenced bundle; they have no receipt bypass option.

A hairpin design set inventories its normalized per-position molecular domains,
resolved hairpin defaults reference, and every byte of every unique member
bundle below `bundle/`. Verification recomputes collection identity, replays
canonical space enumeration, and semantically replays each member. Display
names, descriptive context, segment labels and boundaries, allocation bounds,
and the HTML, CSV, FASTA, and YAML projections do not enter collection identity.
Collection compilation stages authority and projections together and atomically
commits only after complete verification.

The design-set manifest records independent claim statuses for complete space
accounting, replay-verified digital designs, method and destination questions
not evaluated by the package, and construction, quality-control, and activity
evidence not recorded by the package. Verification rejects absent, unknown, or
altered status literals. Human projections render this matrix from the verified
manifest rather than maintaining a second claim authority.

## Limits

Internal exact DNA sequence sets contain at most 256 independent nucleotide
variables and 100,000 reduced decisions. A builder requires explicit positive
decision and computation budgets, capped at 100,000 decisions and 1,000,000
operations. An operation is a per-position domain step, imported decision,
or uncached binary set subproblem. Projection also spends one operation per
visited source decision or terminal, plus the union operations needed to remove
positions before the retained window. Exhaustion raises and prevents that builder
from publishing even a previously obtained handle as a completed set. These
limits bound representation and computation, not molecular feasibility.

Sequence-set serialization rejects cycles, forward references, decreasing
positions, redundant or duplicate decisions, unreachable content, noncanonical
ordering, and incorrect cardinality. Cardinality and member recovery account
for unconstrained positions skipped by reduction. Exact A/C/G/T member rank
can be recovered without enumerating earlier members. Nucleotide-set validity
does not validate the molecular process that would admit those sequences.

Basal source domains preserve recognition context outside the paired adapter
and retained source window. Exact materialization validates placement masks,
source-base restrictions, adapter pairing permissions, future-end bases, and
fixed context before deriving pairing records. Canonical compact source masks
require every pairing position to declare canonical pairing; unsupported pair
permissions raise rather than silently narrowing the population. These internal
domains establish neither molecular admission nor complete search coverage.

Internal compact foldback admission requires a solved finite domain and explicit
decision, set-operation, and recognition-window budgets. The recognition-window
budget is at most 1,000,000 and counts every oriented motif window in every
pre-stage duplex, including discarded terminus products and windows whose cuts
would be unavailable. This inventory is checked before reaction-site scanning.
Exceeding any computation budget raises; it cannot produce an empty completed
set. Exact admission intersects required intended events and excludes every
undeclared actionable event under the shared reaction rules. Substrate topology
or assessment semantics outside the supported sequential single-operation
programs raise instead of being silently classified as infeasible.

A nickase recognition span must remain wholly present after terminus cleavage.
Foldback placement excludes spans removed by that cut before sequence expansion,
including mirrored bottom-strand routes. Cleavage at the recognition interval's
edge or outside it still uses the characterized enzyme offsets and actual
molecule boundaries.

Complete foldback sequence-space requests separately bound retained overhead and
computation. The current execution envelope permits retained overhead through
256 nt, at most 100,000 exact payload/geometry/strand cases and 100,000 examined
programs. Decision and set-operation limits apply separately to each program
admission and each case union; recognition-window limits apply per program.
An additional limit of at most 1,000,000 serialized decisions bounds all stored
program and union sets together. Case cardinality is checked before symbolic
payload expansion, and program traversal does not allocate the program product.
Any exhausted limit raises without a complete result. These ceilings are
computational capabilities, not biological thresholds.

The raw population of one exact foldback case is `4**(A+C)`. Its compact union
counts each admitted independent sequence once across all supporting enzyme
programs. Cases remain distinct by exact payload, A, C, D, and nick strand.
Result loading binds the full request, catalog, implementation versions, roster,
placement exclusions, admitted sets, and totals by deterministic rediscovery.
An empty case with no permitted program remains part of the raw denominator.
An empty geometry envelope has zero cases and zero raw population.

Foldback result v2 also retains each program's joint `source_assignments`: the
independent retained word followed by variable bases in the source tail removed
by terminus cleavage. Both joint and projected decisions count toward the
serialized budget. Concrete partitions and survey continuation use all joint
assignments; a failed source primer does not exclude the other completions of
that retained word. Local admission still does not prove complete-route validity.
The route version is `linear-source-foldback/6`; old result schemas and producer
identities are rejected, rather than resumed with different enumeration addresses.

Complete basal sequence-space requests use the same computational limit contract.
One case fixes exact payload, nick coordinate and strand, and a canonical local
pairing window. Its raw population is `4**(n+W)`; exact end identities and enzyme
programs do not multiply that denominator. The local window must cover the
future-end footprint. The retained-overhead ceiling filters n+W and does not
claim to bound complete material cost. Placement domains may extend outside
that window. Admission checks every oriented recognition window on the full
source before projection removes outside context. Result limits count both
source and local decisions; exhaustion never yields completed absence. Verified
loading recomputes complete request coverage and supporting sets. Member recovery
preserves full adapter recognition context and checks ordinary molecular
realization, including unresolved association obligations.

Every spec has an explicit positive candidate bound. The convenience route
resolves exactly one generic design. Foldback enumeration reports `complete`,
`infeasible`, or `truncated`, including the fired node or hit bound; a truncated
search is never presented as complete. Nicking-placement discovery evaluates at
most `max_search_nodes` caller-owned catalog entries and returns at most
`max_hits`. Its result distinguishes an incomplete catalog search from a
complete search whose returned hit list was bounded; both conditions produce an
explicit `truncated` status. Symbolic expansion calculates exact
cardinality before allocation, raises when it exceeds `max_variants`, and never
truncates silently. Design-space planning likewise calculates the full payload
by foldback by basal by release Cartesian cardinality before allocating rows and
fails above `max_designs`.

A substrate-space preview computes cardinality arithmetically before member
allocation. The scientist surface compiles through its tested 256-design
release envelope. A valid larger space is `blocked`; compilation writes
nothing. V1 does not truncate or publish partial authoritative sets.

Basal candidate discovery calculates the exact left-arm by right-arm IUPAC
cardinality before evaluation. It examines at most `max_search_nodes`, returns
at most `max_hits`, reports reserve and reject exclusions for every examined
non-hit, and distinguishes node truncation from result truncation. Candidate
identity covers the exact pairing request and complete evaluation; result
validation rejects domain, accounting, canonical-ordinal, and order drift.

Payload-centered foldback and basal neighborhood discovery traverses finite
geometry, strand, payload, and enzyme-program domains in ascending absolute
retained-overhead order. Each examined level accounts for candidates as
accepted plus rejected and partitions rejections by observed primary failure
category. Only the final recorded level may be partial. Completion is separate
from feasibility: an exhausted domain is `complete` with either `feasible` or
`infeasible` existence status; an evaluation cap is `truncated`, and an explicit
quota is `stopped_by_policy`. An existence query preserves a witness for each
accessible local work unit without claiming all exact realizations were
enumerated. Projection verification rebuilds level membership and accounting
from the exact source result, so a checksum-consistent subset, reordering, or
extra row is rejected.

Foldback discovery can exclude one enzyme program before expanding its variable
sequence domain when an unintended actionable site lies wholly within the
unchanged payload duplex. Recognition and cut availability come from the same
reaction-state evaluator used by exact replay. Kernel placement failures retain
their precedence. A proven program exclusion contributes one rejected evaluation;
evaluation counts are not the cardinality of the raw sequence population.
Programs without this proof retain their exact sequence enumeration and replay.

Complete construction composition computes the nominal local Cartesian
cardinality before evaluation, examines only its canonical bounded prefix, and
records accepted plus rejected dispositions for every examined combination.
Selected-pair composition instead records the explicit foldback and basal
selection in the request and evaluates exactly that one replay-verified pair;
absent selection fields do not alter exhaustive compilation bytes.
`complete` and `infeasible` require full nominal exhaustion; `truncated`
requires an exact local or composition reason. Accepted realizations remain
separately identifiable even when achieved-geometry or final-product groups
coincide. A trajectory projection requires an explicit accepted realization
identity and never treats canonical order as preference.

Basal processing-geometry discovery evaluates at most `max_search_nodes`
nicking agents and returns at most `max_hits`. Every examined agent has one
feasibility row. The result validator requires full node-budget exhaustion,
exact compatible-hit accounting, canonical agent order, content-addressed hit
projection, and distinct node/hit truncation. Signed release/nick coordinates
remain local geometry; concrete molecular spans remain nonnegative.

Basal processing-route composition evaluates the canonical Cartesian product
of the returned basal candidates and returned processing geometries. It reports
upstream basal or geometry truncation separately from its own node and hit
bounds. `available_pair_count` describes that returned cross-product, not an
unobserved global search space. HOP computes that count arithmetically and does
not allocate pairs beyond the node budget. Every feasibility row and returned
route replays its embedded inputs, retained scar, terminal nick, surviving
strand, content identity, canonical ordinal, and order.

Released-foldback geometry discovery calculates the full agent-pair by release-
orientation by boundary-window cardinality without materializing that product.
It consumes nodes only through `max_search_nodes`, returns hits only through
`max_hits`, and reports either bound explicitly. Validation replays every
examined recognition footprint, cut, foldback pair domain, sequence-space
cardinality, hit identity, canonical ordinal, and order from the embedded catalog and request.
It never reports an unexamined concrete sequence.

Released-foldback precursor search calculates the exact intersection of one
selected geometry and one caller-authored IUPAC template before allocation.
Correlated foldback pairs count as one axis. `max_search_nodes` bounds exact
sequences examined and `max_hits` independently bounds returned candidates;
both limits are replayed from the embedded request. A zero intersection is
explicitly infeasible, and result validation rejects sequence, digest, content
identity, canonical ordinal, order, accounting, or truncation drift.

Resolved release and foldback requests cannot be joined unless
their adjacent sequence states are identical. Release scanners discard any
resolved top or bottom cut beyond the supplied sequence. Search result models
reject terminal statuses that contradict hits or the number of examined nodes.
A release projection cannot enter resolved-junction derivation without a terminal nick.
Component evaluation emits the one-dimensional hairpin-encoding sequence and
produces route-neutral views; it never fills missing method fields from a
catalog search or default.
An absent paired stem extension is omitted from serialized v2 design specs.
When present, its arms, pair calls, two feature spans, and state transition must
all agree. Method-material plans reject terminal-binding or chemistry drift.

## Degraded modes

There is no permissive fallback for an unknown schema, catalog reference,
profile, route, source endpoint, or corrupted bundle. Construction sources are
bounded regular nonsymlink JSON/YAML mappings read through one checked file
descriptor. Duplicate keys and YAML aliases, anchors, and merge keys are
rejected before model validation. Sources dispatch only the exact
`hop.construction-source/v8` schema; the design authority is loaded from a
separate verified bundle path. Each accepted route replays its declared source
ssDNA and two source-preparation primers into the exact duplex that seeds
downstream construction. For PCR-bearing endpoints, a separate policy resolves
the adapter and two endpoint primers in `derive`, `constrain`, or `fixed` mode.
Derived and constrained primers bind invariant construction sequence outside
the payload; constrained reusable handles are caller-authored, not silently
generated or ranked. Direct ssDNA-hairpin routes reject endpoint auxiliaries.
When composition binds a selected replay-verified source partition, route
verification replays its prepared duplex, enzyme definitions, concurrent nick
program, inclusive fragment rule, and required survivors. The built-in SVG
renderer has no plotting dependency and consumes only a typed workflow view.
Optional future renderers may be absent without blocking the typed plan, but
they may not recompute molecular state.

Standalone local-neighborhood requests retain the one-megabyte authored-source
limit and may declare at most 100,000 search nodes and 100,000 realizations.
Portable local-neighborhood results have a separate 64 MiB envelope because
they contain bounded candidate, rejection, and replay evidence. The loader
checks embedded execution bounds before semantic replay. A larger study must
narrow its declared search or use every member of a deterministic, disjoint
sequence-domain partition. Each part remains independently replayable and
cannot claim whole-domain payload compatibility; the loader never treats an
oversized result as a partial authority.
Basal sequence partitions select canonical assignment ordinals before building
molecular solutions. They preserve the unpartitioned outcome order, including
pair-budget failures; a sole placement failure belongs to part zero. Partition
selection changes neither the molecular constraints nor the selected outcomes.
Source-partition result creation and replay enforce the same 64 MiB envelope before
publication or semantic replay; authored requests retain the one-megabyte limit.
External observations may be unavailable without invalidating a prospective
HOP bundle because execution evidence is caller-owned.
