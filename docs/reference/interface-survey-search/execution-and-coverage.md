# Execution, coverage and resume

Choose execution limits, interpret coverage and resume or inspect an existing survey
checkpoint.

Return to the [interface survey search reference](../interface-survey-search.md).

A survey starts with one exact stem and a finite set of permitted end pairs,
junction geometries, methods and material choices. It saves evaluated
combinations and any complete preparations they produce in a checkpoint.
Here, a **domain** is the set of allowed choices, a **population** is a set of
sequence assignments, and a **witness** is one exact solution supporting the
reported claim. A local witness supports its junction; a complete witness also
passes the whole construction.

## Understand what is bounded

Length caps define acceptable scaffold additions; they do not make length the
sole design objective. The design space consists of joint choices of interface,
geometry, sequence permissions and processing methods. Those choices constrain
one another. A loop size or end placement being individually permitted does not
establish that it can be combined with every other permitted value.

Three kinds of coverage answer different questions:

| Coverage | Question |
| --- | --- |
| Interface targets | Does at least one complete preparation produce each requested end pair? |
| Joint parameter choices | Which combinations of geometry and methods have complete witnesses? |
| Exact realizations | Which sequences and preparations realize a supported combination? |

One witness establishes support for its exact parameter combination, but does not
enumerate all sequences that could realize it. Conversely, finding every end pair
does not establish that every permitted geometry/method combination was examined.
The current survey reports interface coverage and retains exact evaluations. It
does not yet provide a compact, complete relation over all joint parameter choices.

Both neighborhoods store local sequence populations compactly rather than listing
every sequence separately. Basal populations
retain source/adapter pairing permissions, noncanonical-pair caps and source-site
constraints jointly. The executor selects admitted members directly and verifies
their exact local and complete constructions. Upstream-context addressing and
whole-route coupling remain separate; the full joint relation is not yet symbolic.
Traversal interleaves both neighborhoods and admitted enzyme programs, so a large
population under the first method does not postpone all other methods. Permitted
gap pairs are visited in increasing summed additions, broadening both ends early.
These are search-order preferences; they neither remove candidates nor establish
that an observed construction is the minimum.

Foldback populations retain both the independent arm/cap words and their
compatible source-tail assignments. The tail is removed by terminus cleavage,
but it can affect earlier sites and source-primer binding. Survey addresses
retain those alternatives until the affected checks are satisfied; a failed
completion is not an exclusion of every preparation with that retained word.
The local facts distinguish `admitted_configurations` (retained words),
`program_supported_members` (retained words counted per program) and
`program_supported_precursors` (source assignments counted per program).
Complete-preparation counts come from whole-route compilation.
## Evaluate and resume

For an authored `survey.json`, provide explicit per-evaluation limits and a batch
size. This command creates a new checkpoint; it refuses an existing file.

```bash
# Evaluate or continue the same checkpoint under the declared limits.
hop-design construction survey evaluate survey.json --index survey.sqlite \
  --max-evaluations 256 --local-nodes 1000 --local-realizations 1000 \
  --release-site-pairs 1000
```

Repeat with `--resume` to continue committed progress. Keep the request, producing
implementation and every per-evaluation limit identical, including
`--continuation-batch-size`. The external `--max-evaluations` allowance may change;
it controls how many additional evaluations this invocation attempts. Changing
`--continuation-batch-size` requires a new index. The complete target catalogue
is independent of these computing limits; there is no 64-target roster limit.
The default database cap is 1 GiB and can be changed explicitly with
`--max-checkpoint-bytes`. SQLite rollback journals and selected
exports require additional temporary disk space.

Evaluation proceeds in rounds combining each target's continuation depth with
new partner pairs. Within a round, missing end words and unsupported pairs take
priority. Supported targets also advance to alternative preparations, even while
other targets remain unresolved. This supplies compensating geometry and method
choices without waiting for complete interface coverage. More time does not
change the declared molecular permissions.

When a diversity objective includes cloning ends or end gaps, HOP first suggests end pairs
from the permitted basal pairing relationships. It tries those pairs before the
ordinary coverage order, while keeping every other permitted pair reachable.
A suggestion still needs a complete preparation to establish support. An explicit
preparation preference takes precedence. Missing or unfinished suggestions do not
establish that other pairs are impossible.

Compact foldback evaluation defaults to 100,000 decision nodes, 1,000,000 set
operations, 1,000,000 site checks and 1,000,000 serialized decisions per result.
The corresponding flags are `--sequence-decisions`, `--sequence-operations`,
`--sequence-site-checks` and `--sequence-result-decisions`. These limits bind the
checkpoint. `sequence_space_budget` leaves the pending evaluation uncommitted and
its target unresolved. A larger limit requires a new execution index, not a new
molecular domain. Coarse cases and sequence alternatives are interleaved; an
enormous first sequence population does not prevent visiting other geometries.

A completed empty basal search can rule out its entire foldback/source-context
plane. The checkpoint retains the exact exclusion proof and reuses it across
that plane.
`certified_empty_planes` and `certified_empty_branch_cells` report this scoped
coverage separately from molecular continuations actually examined.

For `paired_scaffold_completions`, a bounded preliminary check also postpones
foldback geometries with proven-empty local populations. This applies with or
without a diversity objective. It checks at most 128 cases, bounded further by
`navigation_nodes`, and reuses the resulting local authorities. Unknown and
unexamined cases keep their ordinary priority; postponed cases remain reachable.
Local support still requires a complete construction attempt before admission.

`--navigation-nodes N` bounds each successor seek. When that allowance is spent,
a navigation checkpoint preserves the exact position and counts zero molecular
continuations. Resume continues from there. A completed witness or exclusion is
retained even if admission of the next geometry reaches a sequence-space limit.

For `paired_scaffold_completions`, `--navigation-frontier N` separately bounds
pending geometry, group and unfinished-completion entries (default 4096,
maximum 100000). `navigation_frontier_budget` leaves the current evaluation
uncommitted and the target unresolved. This limit is checkpoint-bound; increasing
it requires a new index. It is a memory/work bound, not a molecular length cap.

Use `--continuation-batch-size N` to group up to N canonical continuations
(default 1, maximum 1024) into one committed evaluation. A batch advances through
proved empty local cases, retaining their diagnostics, and stops at the first
nonempty candidate even if its complete construction fails. Inspection includes
these preceding cases in `skipped_empty`; molecular replay checks each one.
Unresolved local searches cannot be skipped as empty.

The completion objective uses the same limit to group navigation and proved empty
local steps before one complete-compilation attempt. It stops at that attempt,
including a rejection, or when a navigation seek spends its node allowance.
Inspection retains the preceding steps; replay verifies their requests and proofs.
Batch size 1 keeps navigation and molecular attempts in separate commits.

`max_evaluations` counts committed steps. `continuations_examined` and
`new_continuations_examined` count committed canonical continuations, separately
from steps; work discarded within an uncommitted batch is not included.
Compare these counts when changing batch size: more work per commit
also changes how deeply each scheduled target is explored. Batch size is a
checkpoint-bound execution limit, so changing it requires a new index. A resource
stop or source change inside a batch leaves its step uncommitted; the preceding
commits remain resumable. Increasing this limit does not alter molecular scope.

The returned JSON separates supported pairs, scoped exclusions, unresolved pairs,
unexamined pairs and supported words on each side. Multiple preparations for one
pair count once toward pair coverage. A checkpoint-cap stop leaves the uncommitted
evaluation pending; resume with more capacity. A local population-limit error
requires a new execution with larger relevant sequence-space limits, using the
same molecular request. Neither condition is an exclusion of the target.

To inspect saved attempts without replaying the molecular route:

```bash
# Inspect checkpoint progress without replaying the molecular search.
hop-design construction survey inspect survey.json --index survey.sqlite \
  --offset 0 --limit 100
```

Each row's `evaluated_local_pair` identifies the foldback and basal realizations,
their enzyme identities and achieved geometry actually sent to the complete
compiler. It is null for navigation or empty local admission. The accompanying
`outcome` and `witnesses` distinguish a rejected complete attempt from returned
preparations. A permitted catalog or locally supported population is not evidence
that all its programs received a complete attempt. Inspection checks saved object
integrity and local-result bindings; use survey verification for molecular replay.
