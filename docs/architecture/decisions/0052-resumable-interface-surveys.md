---
doc_id: hop-adr-0052
title: Resumable complete-interface surveys
intent: Separate the molecular target domain from incremental evaluation and indexed storage.
audience: [maintainers, integrators]
owner: HOP Design maintainers
status: accepted
last_verified: 2026-10-10
doc_type: explanation
---

# Resumable complete-interface surveys

The small-roster discovery packet is useful for inspecting a few requests. Its
entry limits, prefix continuation and copied drawings cannot define the scope of
an interface-coverage study. A four-base interface domain contains 256 words per
side and 65,536 ordered pairs. All targets must remain accounted for even when a
single invocation evaluates only part of that domain.

## Decision

`models/construction/surveys` owns the strict molecular request and target
addressing. `design/construction/surveys` owns incremental execution, its disposable
scheduler, compact checkpoint and replay. The existing product, local-neighborhood
and complete-construction contracts remain the molecular authorities. The survey
adds no reaction or alternative feasibility evaluator.

The request authors one invariant stem; separate strand frames; a Cartesian word
domain; joint left/right placements; foldback geometry; basal nick and association
permissions; enzyme policies; material policies; and local/whole-route constraints.
Per-evaluation quotas and checkpoint storage limits are execution inputs. They do
not remove targets from the molecular domain or establish molecular exclusions.

A branch addresses an exact coarse foldback geometry/strand, joint placement,
basal nick offset, association requirement, jointly permitted duplex release
method and exact permitted source context. Source
contexts retain canonical length/lexicographic addresses. Traversal interleaves
the first assignment at each permitted length before the second assignment at
each length; finite shorter domains drop out without delaying longer contexts.
Within each length, the executor first visits contexts that place the exact
left release recognition and end footprint for the selected basal source member.
This is an invertible preference: nonmatching contexts remain in the same finite
domain with their original canonical addresses. Added primer sequence or another
embedding may make such contexts useful. A missing local window or a context-set
budget limit falls back to ordinary ordering; it cannot establish a whole-route
exclusion. Both directions of the combined permutation are counted algebraically;
earlier assignments are not generated. The first cursor, continuation and replay
use the same page-specific mapping, including a nonzero initial context address. Foldback programs are selected from their
compact admitted populations and replayed through ordinary local enumeration.
Basal programs likewise retain joint source/adapter populations. Nickases cannot become duplex release
methods through an unrestricted provisioning policy. A duplex method with an
incompatible end length remains subject to the ordinary molecular evaluator.

Foldback admission reuses the existing complete `SequenceSet` population solver
within each coarse case. A page selects an admitted program/member, recovers its
raw placement address algebraically, and then uses ordinary local discovery and
complete construction replay. Compact local support cannot itself create a complete
witness. Empty complete populations can exclude that local branch; a decision,
operation, site-check or serialized-result limit leaves evaluation unresolved.
The four sequence-set limits are separate, bound execution inputs. Cached compact
populations include their complete request and limits and replay before reuse.
Program/member traversal visits the first member of every nonempty program before
the second member of any program. Unequal population sizes are counted
algebraically, so large sequence sets cannot delay every other enzyme program.

Before selecting individual foldback sequence members, the survey also checks
an exact necessary source-primer condition for each supported enzyme program.
Every member of that program shares its source-expression length. The interval
outside the supplied payload is available to the reverse primer for a top-strand
foldback nick, or the forward primer for the mirrored bottom-strand case. The
minimum permitted primer length is taken from the declared fixed, derived or
constrained policy. Sequential terminus programs can have longer precursor DNA
than single-cleavage programs with identical final geometry; the check uses the
full source expression, never only an A/D/C formula.

Local molecular admission remains unchanged. The evaluation separately records
`source_primer_admission` with program identity, primer role, available/required
lengths and admitted/excluded member counts. If every supported program lacks
the necessary span, no basal population or whole construction is evaluated for
that local page. The ordinary source-preparation and complete-route checks still
validate retained candidates. This condition neither establishes complete support
nor excludes a different foldback program or the whole receiving-end pair.
Replay recomputes both the compact admission and its dependent page addresses;
changed primer policies cannot reuse a prior filtered population. This does not
add an exclusion spanning all outer source-context or geometry coordinates.

Basal admission conditions full-source sequence decisions on intended and
unintended nickase sites. Each source base retains its permitted adapter partners;
a weighted suffix count enforces the global noncanonical-pair limit jointly.
It neither replaces noncanonical permissions with matches nor expands all adapter
strings. Exact members are ordered by full source, adapter and remaining context,
then mapped algebraically back to the ordinary raw candidate address. The public
canonical-only basal population contract keeps its original scope. The survey
uses the shared source-site admission and a separate internal joint population.
Invocation-owned caches bind the entire product or local request; sequence limits
are fixed for that invocation. Source-context orders additionally share work
across pages only when the exact source window, payload boundary, enzyme definition,
release action and authored context policy agree. Cache eviction changes cost,
not addresses or coverage. Branch translation additionally retains up to 16
validated product requests and 2 MiB of canonical request bytes per invocation.
Its key includes target, complete branch address and every evaluation limit; the
survey request is fixed on the translator. Address validation precedes lookup,
including rejection of Boolean and non-integer addresses. Oversized products are
returned without retention. Reusing a strict immutable request does not skip local
or complete molecular admission, proof replay, or producer verification.
These byte bounds measure serialized content, not total Python resident memory.
The foldback population cache retains at most 128
entries and 2 MiB of canonical result bytes. Python object overhead and up to
eight population references in the independent product-plan cache are additional.
Oversized populations remain usable but are not retained in that cache. Reopening
an index admits its saved populations afresh. Empty complete populations can
exclude the proved local domain described below. Program, decision, operation
and result limits raise rather than appear
as empty molecular support.

Selected foldback and basal members are replayed through existing
[exact partitions](0030-partition-exact-local-sequence-domains.md). A page selects
one admitted program/member per neighborhood, or records a complete empty local
population. The selected raw addresses preserve the ordinary compiler's authority.
Pair cursors then traverse complete continuations. Source-context position,
actual molecular-variable displacement, and both local population coordinates
advance in one diagonal wave. Canonical branch and page ordinals remain stable
addresses; neither becomes a displacement. Placement cost sums left/right
allowed-value rank distances from the preferred declared pair. Foldback cost
sums A/D/C/strand and explicit-loop-word rank distances from the preferred legal
case. Other coarse coordinates retain their declared ordinal costs. Only legal
cases already in the roster participate; distances never invent cross-permissions.
Ties use canonical coordinate tuples and local-page order. Sparse joint rosters
can leave empty interior waves, so exhaustion also requires passing every branch
introduction. An empty early wave cannot exclude later declared cases.
The optional `continuation_batch_size` execution limit groups up to 1,024
canonical continuation checks into a committed evaluation (default one). Only
proved empty local populations and explicit molecular contradictions may precede
the terminal check. The first nonempty local pair stops the batch, including when
whole-route compilation rejects it. Truncated zero-result local searches are not
proved empties. Every skipped address retains its local facts, rejection, cursor
and exhaustion flag; aggregate replay recomputes the full contiguous chain.
Only the terminal product request needs a stored authority object.

`max_evaluations` bounds commits; progress separately counts canonical
continuations examined. Larger batches change scheduling depth relative to target
coverage, and are not equal amounts of molecular work. The batch cap binds the
checkpoint. Producer bytes are checked before each commit; an exception discards
that batch's uncommitted step, while prior commits remain. Reaching the cap keeps
the next cursor unresolved. Only the ordinary finite cursor and complete proof
chain can establish exhaustion. Caches may retain uncommitted work; they cannot
alter which addresses replay visits.

Complete empty basal populations additionally support `hop.empty-basal-plane/v1`
certificates. One certificate fixes the target, joint placement, nick offset,
association requirement, release method and release projection. Foldback case
and canonical source context remain free because neither changes the complete
unpartitioned basal request. The certificate binds that typed request, survey,
producer, evaluation limits and recomputed admission facts. It cannot be made
from a selected sequence partition, a stopped search or a rejected whole route.
Certificates have distinct canonical scopes; their branch-cell counts are not
additional molecular continuations or complete preparations.

Only certificates in a target's committed history affect later navigation.
The current step may use its newly proved certificate transactionally; a failed
commit cannot make it reported evidence. Resume re-admits each saved certificate;
aggregate verification independently regenerates both proofs and successor
positions. Cache warmth never supplies exclusion authority.

`navigation_nodes` caps one successor seek (default 256). A molecular batch can
perform at most `continuation_batch_size` such seeks. A pending
`hop.interface-survey-seek/v1` stores wave, context position, geometry and page
predecessor. Navigation-only commits use `hop.interface-survey-navigation/v1`
and count zero molecular continuations. Local page seeking uses direct coordinate
arithmetic instead of restarting a long diagonal. An exhausted cursor preserves
any earlier incomplete-coverage flag. Complete certified coverage of every basal
plane ends navigation without expanding the context domain.

Molecular evaluation records use `hop.interface-survey-evaluation/v2`, including
new certificate references and explicit continuation counts. A later navigation
admission limit preserves an already completed molecular evaluation with a seek
cursor. `navigation_nodes` sums the successfully counted seeks;
`navigation_nodes_complete=false` and `navigation_stop=sequence_space_budget`
identify a later interrupted seek whose work is not included. Inspection preserves
both fields, so a known subtotal is never presented as an exact total. Producer/limit binding rejects incompatible older checkpoints; recorded
canonical molecule addresses remain unchanged, while target scheduling and
commit prefixes can change. Partial-plane pruning avoids molecular admission
but still visits individual eligible geometry coordinates; it is not a compact
joint solution of every whole-route constraint.

Each context is an explicit restriction of the original material permission;
it is checked again when a witness is retrieved or an evaluation is replayed.
Source contexts and cross-neighborhood whole-route constraints are not yet one
compact joint relation; local population admission must not be described as
exhaustive whole-preparation conditioning.

Within a local page roster, foldback and basal member coordinates also advance
diagonally. The six coarse branch dimensions retain direct total-displacement
rank/unrank addresses, independently of the molecular visitation costs.
Declared gap pairs are ordered by their summed paired additions, then
left and right gap, without inventing undeclared combinations. Foldback cases
prefer those whose geometry estimates enough source reverse-primer span; this
is only a scheduling preference. Exact replay owns the span and its validity,
and shorter estimated cases remain in the roster. These orders improve access
to compensating alternatives; none proves a global minimum or full coverage.

## Conditional auxiliary completion

The optional request field `source_context_objective` is `all_words` by default
and omitted from canonical serialization at that default. The explicit
`paired_scaffold_completions` objective enumerates local molecular assignments,
context lengths and consequential context sequence, seeking one complete handle
per group and local pair. It preserves basal pairing and released-insert sequence,
not every exact unpaired hairpin sequence or material set. Query and progress
projections name the objective; `all_preparations_enumerated` cannot become true
under the completion objective. Request identity binds this choice.

In the supported payload-forward source frame, let B be the local prefix before
the stem, n the bottom-strand nick offset, M the required association span
(including the local paired span), g the left released paired gap and k its
protruding-word length. Protect the context suffix of
`max(0, n + M - B, g + k - B)` positions. Binding requires the exact local source
and nick boundaries, explicit association and the supported right basal-release
frame. Unknown frames protect all positions. PCR copying changes ancestry without
removing sequence dependence. Compact exact sequence-set projection and recovery
retain correlations; independent base marginals cannot be recombined.

Recognition and end-footprint preferences project onto protected suffix groups
before selecting a group, then order complete context words within that group.
Projection first intersects the preferred words with the permitted full sequence
set. Each suffix group appears exactly once, followed by nonpreferred groups;
all permitted words remain reachable. Ordering only words inside a lexicographic
group can postpone compatible surroundings behind a large unrelated background.

The optional `preferred_source_contexts` roster adds a separate completion
preference: at most 16 exact caller-owned words, each at most 256 nt. It is bound
to the request and omitted when empty. Within each existing length/protected
suffix group, intersect these words with the admitted correlated domain and try
them before the recognition-preferred and remaining completions. Subtract each
earlier tier from the later tiers, retaining every canonical word address once.
The roster never changes group order or expands molecular permissions. Exact
site-exclusion seeking traverses these same tiers, so failure of a preferred
completion cannot eliminate the rest of its scaffold family. Reject this roster
for `all_words` or an exact/derived source policy rather than silently ignoring it.

The optional `source_handle_seed` addresses a different need: reuse the same
starting auxiliary sequence across protected scaffold groups, allowing changes
where constraints require them. It accepts 1–256 exact caller-owned bases. For
each group, truncate the seed to its unprotected prefix and order completions by
Hamming distance over covered positions, then A/C/G/T word order. Positions beyond the seed retain ordinary
ordering. No protected suffix, length, sequence membership or canonical address
changes. Exact preferred-context words still precede this traversal. The seed
binds request identity and is rejected under unsupported objectives or source
policies. A bounded attempt does not establish the globally closest complete
preparation or primer performance.

The kernel counts distance layers over the existing reduced sequence decisions.
Free suffixes use exact binomial counts; correlated branches retain their joint
permissions. Memoized states are local to that ordering object and bounded by
the existing sequence-set operation limit. Exhaustion raises a resource stop,
not molecular absence. Proven site-conflict subtraction
uses the same order, avoiding enumeration of an excluded block. The scheduler,
compiler, checkpoint and replay retain their existing responsibilities. Public
CLI, optional-intent API and atlas retrieval consume that single request. The
shipped insert context uses its existing synthetic example handle as a seed;
application-specific presets remain caller input, outside the public package.

The completion frontier merges geometry introductions, local pages, conditional
groups and unfinished pair attempts. Its wave adds geometry cost, page depth,
group, local-pair ordinal and attempts already made. New local pairs enter lazily
after the preceding pair's first attempt; retrying that pair does not prevent
other groups or pairs from advancing. Every finite task has finitely many
predecessors. A proved multiword skip advances the canonical member address but
counts as one attempt for scheduling. The strict `hop.context-group-seek/v4`
cursor preserves pending work across cold resumes and rejects duplicate pending
attempts for one pair. Replay recomputes the frontier and every selected address.

Before foldback expansion, a basal introduction tests the necessary joint end
relation once for its placement, nick, association length, method and projection
frame. Contradictory frames introduce no foldback stream. Admitted and
untranslated frames introduce every authored foldback case in cost order; a
failed complete preparation does not discard the remaining alternatives.
`basal` and `foldback` frontier entries keep these two operations explicit and
resumable. Each popped introduction consumes one navigation node, including a
necessary-relation check; there is no uncharged nested molecular scan. The
original combined geometry/page/group/attempt ordering remains fair. A saved
v3 cursor cannot be interpreted as a v4 search.

Recognition-only obligations narrow the same base domains directly, including
complemented aliases and contradictions in auxiliary variables. They do not build
and then flatten an intermediate decision graph. The joint end projection still
enforces source/adapter contact tables and the total noncanonical budget; those
relationships are never replaced by independent base choices. Frame length and
output graph limits remain enforced. Removing an intermediate graph changes its
resource cost, so a former resource stop may now complete under the same limits.

An invocation-bound basal-frame index reuses established end-pair relations before
lowering another exact target request. Its key omits only foldback geometry;
request and all execution limits remain bound. Target and all geometry coordinates
are validated before lookup. Unsupported translations are not cached as empty
relations, and target membership is derived from the relation on every call.
This additional index retains at most 4,096 entries and 2 MiB of canonical relation
bytes; Python object overhead is additional. Eviction changes cost, not evidence.

Exact-cost geometry recovery avoids repeated scans of earlier cost layers. Node
and pending-entry budgets remain distinct. `navigation_frontier` defaults to 4096
and is capped at 100000; reaching it leaves the evaluation uncommitted and the
target unresolved. It binds the checkpoint. `continuation_batch_size` bounds
navigation and proved empty local steps grouped before one whole-route attempt.
The first compilation, including a rejection, ends the batch. A seek that spends
its node allowance and an unresolved local result also stop it. Thus a large
batch cannot silently multiply one unfinished seek's navigation allowance.
Preceding records are content-addressed individually, their proof references
are retained on the committed record for cold resume, and replay checks every
preceding request and record. Batch size 1 preserves separate step commits.

An ordinary rejected complete compilation may provide an initial-source
recognition exclusion. The proof owner re-derives the exact full duplex and
actionable, undeclared first-stage binding. It projects the recognition predicate
onto context bases while retaining fixed neighboring bases, orientation, boundary
spanning and degenerate motifs. Source-partition routes, later-stage conflicts and
unproved frames supply no such exclusion. Learned predicates apply only to the
same local pair and length-bound group. Compact set difference finds the next
unexcluded member without enumerating skipped words. Surviving candidates still
use ordinary full compilation; failure of one candidate never excludes a group.

Before context projection, `kernel.construction.release_constraints` derives necessary
endpoint recognition and cohesive-word constraints in an explicitly bound
payload-forward, bottom-nick frame. Shared source variables retain their identity
through copying and reverse complementation into distal adapter sequence.
Endpoint-primer handles are part of the projected final duplex. Each side unions
all permitted release actions before both sides are intersected; independent
base marginals must not replace those joint alternatives. Unsupported adapter
policies or coordinate frames return no filter. Sequence-set resource exhaustion
raises and remains unresolved; it is never an empty molecular domain.

`ContextCompletionPlan` intersects that necessary set with the authored context
population before grouping. Canonical full-word ranks retain their original
length/lexicographic addresses, including skipped lengths. Navigation advances
past proved empty pages and records authored/admitted context counts for replay.
Complete compilation is still required for every surviving candidate, including
site uniqueness, other recognition conflicts, primer compatibility and chemistry.
This conditioning applies only to the completion objective.

`kernel.construction.release_population` applies those shared expressions before
individual basal selection. Context variables are appended to the local
source/adapter variables, constrained jointly, then existentially projected away.
The union covers every authored context length and IUPAC permission, not the
exact representative context used to address a branch. Disjoint decision paths
restrict the existing weighted basal population while preserving source-reaction
admission, conditional adapter contacts and the global noncanonical-pair limit.
The original sequence index remains the authority for exact raw addresses.

`ProductParts` retains its original basal population and a separate conditioned
candidate view. Candidate pages use contiguous admitted ordinals; selection,
context binding and complete continuation use that same mapping. Endpoint-empty
populations are skipped with `endpoint_population_admission` records, never
converted into `EmptyBasalPlane` certificates. Replay recomputes the restriction.
Unknown frames retain the original program population; decision-path or sequence
budgets raise and leave the affected search unresolved. No external solver or
change to the public request syntax is required.

Before local admission, `completion.interfaces.EndPairRelations` can reject an
exact end pair using a shared necessary relation. The translated scope is one
release enzyme, forward-left/reverse-right five-prime ends, the established
bottom-nick/source frame, constrained source contexts and default distal adapter
pairing. Other frames retain ordinary evaluation. Unknown translation or a
resource exception never becomes a completed empty relation.

The kernel defers exact end-base binding while retaining recognition and source
placement permissions. Deferred domains cannot materialize exact molecular
candidates. It projects copied aliases and conditional source/adapter factors
onto the two end words, eliminating auxiliary bases existentially; a small
budgeted dynamic program preserves the total noncanonical-pair limit. Shared
recognition/cut-window derivation remains in `release_constraints`.

The invocation-owned cache preserves all request dependencies except exact end
words, the declared full source-context envelope in place of a branch's chosen
context, foldback geometry outside the proven flank frame, and display name.
It holds at most 4096 entries and 2 MiB of canonical relation bytes (Python object
overhead is additional). There is no cross-invocation trusted cache.
`end_pair_admission` records the requested pair's membership, necessary pair count
and relation digest. Basal admission facts use the canonical geometry address
with foldback coordinate zero; that address is a representative for the
necessary relation, not a selected or verified folded product. Replay recomputes
the facts and introductions. These facts neither claim local
reaction impossibility nor create `EmptyBasalPlane` certificates. Surviving
candidates retain ordinary local, source-preparation and complete-route checks.

The kernel owns sequence grouping, models own strict cursors, and
`design.construction.surveys.completion` owns binding, navigation, scheduling and
compilation orchestration. Default all-word traversal remains separate. This is
not a general constraint solver for every whole-route failure, a guarantee of
practical exhaustive completion, or an experimental primer-design assessment.

## Storage and authority

Survey request v2 makes `release.basal_projections` a nonempty, canonical,
duplicate-free roster. Recognition-site ownership is an explicit branch
coordinate, independent of the paired end-to-stem placements. A selected product
request retains exactly one `basal_projection`. The source-contact coordinate
frame depends on the bottom nick and projected end, not on recognition ownership.
Both source-duplex and endpoint-material obligations retain exact molecular replay.
V1 requests and old producer-bound indexes are not relabeled or silently upgraded.

The SQLite checkpoint binds the canonical request, catalogue, producer source and
runtime dependencies, and local/release evaluation limits. Resuming with changed
bindings fails. A batch budget and checkpoint capacity can change between
invocations. Only one executor should write an index at a time; transaction-level
step continuity prevents two writers from committing the same address.

Content-addressed, compressed records share exact local results and construction
artifacts. Local reuse keys include every canonical local-request dependency and
cached authorities are replayed before reuse. Completed evaluations commit
atomically. An interrupted evaluation can leave unreferenced deduplicated objects;
it cannot add supported or excluded targets. No drawings are generated during
survey execution. Selected retrieval replays the ordinary bundle, checks its
request and local-pair address, and produces the normal preparation export.

Integrity checking detects corrupt bytes and inconsistent checkpoint bindings.
It is not a substitute for molecular replay: the public `verify` operation
recomputes every recorded evaluation, cursor and authority in temporary storage,
then derives coverage from that replay. This distinction stays explicit in index
inspection. Rehashed premature exhaustion must fail replay.

## Coverage and ownership

One or more complete witnesses support a target once. A target without a witness
is excluded only when all declared branches, local parts and complete pairs have
finished without truncation. Every other target remains unresolved, including
unexamined targets. Marginal left-word, right-word and ordered-pair counts are
separate. Neither local support nor a failed continuation establishes complete
support or universal impossibility.

The queue interleaves evaluation depth with diagonal partner bands: each band
visits every left word with a rotated right partner. Bands enter in exponentially
widening groups: band 0 at wave 0, band 1 at wave 1, bands 2–3 at wave 2, bands
4–7 at wave 3, and so on. A target's wave is its band's introduction wave plus
its number of prior evaluations. Within a wave the queue prefers missing
marginal words, then unsupported pairs. Making the wave the outer
priority prevents unresolved targets from indefinitely postponing alternative
preparations for supported targets. It also retries compensating continuations
before repeating an unsuccessful initial branch over the entire pair roster.
Every finite pending address remains reachable. This is a traversal preference,
not a change to molecular permission or evidence status.
For a fresh 256-by-256 roster whose targets remain open, every pair receives an
attempt within 130,816 evaluations. The former linear band introduction required
8,421,376 evaluations under the same condition, leaving most pairs unexamined
while early bands accumulated retries. Widening preserves compensating retries
without that quadratic first-visit delay. This bounds scheduling work only, not
molecular computation or the evaluations needed to find complete witnesses;
execution budgets can still stop a run earlier. Existing checkpoints remain
bound to their captured producer and must not be relabeled after this change.
The queue is rebuilt from committed outcomes and does not own evidence. Its
monotone heap must match the reference priority scan. Overhead preference
projections and linked figure composition require their own acceptance evidence;
this executor does not claim minimum overhead.

## Conditional coordinates and exact atlas

Each complete witness retains compact parameter facts, exact product identities,
material roles and separate retained/material overhead measures. These facts are
derived from the ordinary complete authority and checked during aggregate replay.
The read-only query uses the shared parameter registry. It exposes declared values
even without a witness and retains complete context paths outside the active
filter. Node counts exclude the predicate on that node's own axis; path membership
applies every predicate. A missing witness is unresolved unless the entire declared
search has finished with proof. A failed continuation alone cannot exclude a value.

On-demand atlas inspection and retrieval consume the same typed selection
document, including the exact target/step address and materialized identity. It rehydrates and replays that witness, checks the
stored plotting facts, then uses the shared molecular atlas, parameter-location
and teaching projections. Retrieval and inspection share witness admission.
Candidate reconstruction binds the survey request independently of checkpoint
storage. This preserves endpoint-conditioned local populations and page addresses
when replaying a selected witness without writing caches to the saved index.
An explicitly supplied request must agree with the index if both are provided.
The teaching projector accepts explicit nonspatial context, so neither operation
needs a small-roster discovery wrapper. Drawings remain absent from survey execution.

An optional exact reference selection uses that same admission and replay path.
The shared `projections/atlas_comparison` owner compares both verified routes;
the small-pool variant explorer is an adapter to this owner. The packet retains
both receipts, exact regional and endpoint sequences, changed materials and
terminal chemistry. Regional additions follow recorded copy ancestry. Additional
endpoint edit marks apply only at that endpoint: newly retained insert bases do
not imply that the earlier hairpin gained bases. Unresolved correspondence remains
explicit and cannot supply an animation or camera anchor.

The file query performs cold index admission on each call. Interactive clients
can retain an `InterfaceSurveyChoices` snapshot instead: admission validates the
index within one read transaction, and mapping queries project its immutable
compact records without reopening molecular files or running searches. The
snapshot digest binds its request, producer, evaluation history and coordinates.
A resumed index requires an explicit reload to become visible. This prevents a
concurrent append from mixing earlier coordinates with later coverage counts.

Snapshot integrity remains distinct from aggregate molecular replay. Selected
atlas inspection and material retrieval still replay their exact authority.
The current snapshot holds all complete-path facts in memory; large-corpus
responsiveness and print composition require separate
acceptance evidence.

## One selected trace across surfaces

`InterfaceSurveyChoices` owns `query`, explicit `select`, and seeded `sample`.
The CLI delegates to those same operations. Selection emits a portable
`hop.interface-survey-selection/v1` reference: request, record and query digests,
typed predicates, exact address and preparation identity. Atlas and retrieval
check those bindings before molecular replay. Replay also verifies the stored
plotting facts against the recovered authority; rehashing a misleading projection
cannot satisfy a selection with false coordinates. Both exports retain selection.

The snapshot digest records selection-time context, not a certificate for later
aggregate coverage. Appending evaluations preserves the exact selected record.
Users reload choices explicitly for a new landscape. Sampling hash-ranks distinct
matching preparation identities with a caller seed; duplicate records have one
weight. It samples neither product identities nor unexamined assignments. A zero
match raises without search, nearest-neighbor substitution or requirement relaxation.

This replaces the unreleased survey atlas/retrieval address-only calls. The
small-roster family and comparison operations remain: surveys do not replace
required-member sets, hairpin endpoints or material-reuse semantics.

Callers own scientific bounds and their rationale, exhaustive-survey claims,
application policy and figure selection. HOP owns reusable traversal, verification
and exact retrieval. The small-roster discovery workflow retains its original
contract; comprehensive surveys use this explicit entry point.

## Browser transport

`SurveySession` is a thin loopback adapter over the same admitted choices and
selection operations. Its action token binds both snapshot and query. Exact
selection, sampling and retrieval reject stale tokens; retrieval uses the
server-retained selection after comparing the caller's receipt. Compatible
query/reload transitions replay and publish a matching atlas receipt atomically.
A replay failure leaves the previous interaction state intact. The output is
create-only and may not traverse symbolic links. Existing local Host, Origin,
per-server authorization, bounded-body and generated-file restrictions apply.

Comparison caching includes reference and selected identities. Query rebinding,
repeated selection and reload preserve the established reference. The camera
uses unique recorded correspondence to preserve an inspected position and zoom;
otherwise it can preserve a unique processing phase without inventing a base
match. A failed drawing load clears the displayed molecule and disables retrieval
until a successful render. Obsolete drawing responses, including rejected
responses, cannot replace the current view or its status.

The surface has one parameter plot and one full molecular atlas. Query code and
CLI replay are progressive disclosures; it does not initialize the small-pool
comparison, envelope authoring or molecular edit and comparison panels. Its camera and parameter
hover have no access to query mutation. This unifies the survey journey without
deleting distinct family and direct-hairpin capabilities.
