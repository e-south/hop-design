# Survey auxiliary completion

This part of the survey decision records completion objectives, necessary sequence
relations and the proofs that may prune permitted assignments.

Read the [parent decision](../0052-resumable-interface-surveys.md) for its context and
the other topic records.

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

### Necessary constraints before complete construction

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

### Shared end-pair screening

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
compilation orchestration. Default all-word traversal remains separate. Other whole-route
failures still require complete compilation. Finite execution budgets can leave
the declared domain unresolved.
