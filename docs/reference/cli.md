# CLI reference

Start with the [worked discovery example](../guides/discover-designs.md). The
signatures below use placeholders such as `DNA`, `DESIGNS` and `NEW`. Replace
them with your sequence and paths; output directories must be new.

## Discover complete designs

```text
# Inspect effective permissions, then discover complete preparations.
hop-design design resolve --stem DNA --product released_insert --out NEW
hop-design design discover --stem DNA --product released_insert --out NEW
hop-design design discover --request INTENT.json --out NEW --evaluations 64
# Continue the saved search or filter its recorded results.
hop-design design continue DESIGNS --evaluations 64 --progress
hop-design design query DESIGNS --query FILTERS.json
# Record a selection before exporting its figures and materials.
hop-design design sample DESIGNS --seed 1 --out SELECTION.json
hop-design design select DESIGNS --preparation ID --out SELECTION.json
hop-design design preserve DESIGNS --reference SELECTION.json --stage hairpin --except-neighborhood loop --out REFINEMENT.json
hop-design design compare DESIGNS --request COMPARISON.json --query REFINEMENT.json --out ASSESSMENT.json
hop-design design select-set DESIGNS --comparison ASSESSMENT.json --set-label set-0001 --baseline MEMBER --out SET.json
hop-design design figure DESIGNS --selection SELECTION.json --out NEW
hop-design design atlas DESIGNS --selection SELECTION.json --out NEW
hop-design design retrieve DESIGNS --selection SELECTION.json --out NEW
hop-design design view DESIGNS --out NEW
hop-design design freeze DESIGNS --compact --include-landscape --out NEW
hop-design design freeze DESIGNS --compact --source-contract SOURCE.json --out NEW
```

`design freeze` captures recorded preparations. Optional `--source-contract`
binds a completed discovery from its original producer for read-only export;
it does not relax continuation or replay admission. See the
[edition guide](../guides/share-atlas-edition.md) for input bindings and scope.

`--left` and `--right` are optional exact end constraints for a released insert.
`--context` chooses a versioned context or context file. Use molecular flags or a
request file, not both. `hairpin` and `adapter_ligated_hairpin` request their actual
hairpin endpoints without release requirements. Continue resumes discovery under
the same permissions. For hairpins, `--first-choices N` stops after N new complete
preparations or the evaluation limit; it selects nothing and retains failed
attempts. Each hairpin call examines at most 64 local pairs; subsequent calls retain
the earlier snapshots. Start with the
[complete-design tutorial](../guides/discover-designs.md).

For an exact-stem `discover` or `continue`, `--progress` streams
`hop.discovery-progress/v1` JSON lines to stderr while preserving the final result
on stdout. Counts refer to committed evaluations, not successful designs or
exhaustive coverage. The first Ctrl+C requests a stop after the current molecular
evaluation; a second forces interruption. Resume saved work with `design continue`.
This option is not available for family allocation or `discover --revision`.

A released-insert request file may include `prefer_preparation` with
`bundle_path` and `selection_path` pointing to a verified construction and its
construction selection. This tries the supplied preparation through ordinary
discovery while retaining the broader permissions. The request captures those
inputs so `design continue` does not depend on their original location. See the
[API contract](python-api.md#discover-complete-designs) for this optional preference.

`discover`, `continue`, `query` and `compare` accept `--format auto|text|json`. The default
`auto` prints a concise explanation on a terminal and preserves the full JSON
result when piped. Pin `--format json` in automation. Text output identifies
available molecules and next commands; it never creates a selection. Exclusion
within the saved context calls for an explicit request/context revision, rather
than another unchanged continuation.

For hairpin discoveries, `preserve` creates a new stage-specific refinement from
an exact selected molecule. Use that file with `--query` throughout the existing
workflow. `compare` requires named members and an assessment budget; its output
lists available sets without selecting one. `select-set` records explicit
membership and a named baseline. `retrieve --selection SET.json` exports the
whole comparison, while each named member selection can drive its own figures.
The [loop comparison example](../guides/discover-designs.md#compare-loops-while-holding-the-scaffold)
defines the request fields. These operations do not start a search.

## Conditional variants

```text
# Inspect or evaluate conditional alternatives from a saved result.
hop-design construction variants RESULT --stage hairpin --focus loop --out NEW
hop-design construction variants RESULT --query QUERY.json --out NEW
hop-design construction evaluate-parameters RESULT CHOICES --max-branches 4 --max-continuations 1 --out NEW
hop-design construction parameter-values RESULT CHOICES --parameter loop_word --length 4 --prefix AA --out NEW
hop-design construction revise-envelope RESULT CHOICES REVISION.json --out NEW
hop-design construction evaluate-envelope RESULT PREVIEW --max-branches 4 --max-continuations 1 --out NEW
hop-design construction select-variants RESULT CHOICES --member NAME=OPTION --baseline NAME --out NEW
hop-design construction preview-variant RESULT CHOICES --variant VARIANT_ID --state cleaved_duplex --out NEW
hop-design construction inspect-variant RESULT CHOICES --option OPTION --state endpoint --out NEW
hop-design construction atlas RESULT CHOICES --option OPTION --out NEW
hop-design construction compare-variants RESULT CHOICES REQUIRED.json --out NEW
hop-design construction select-variant-comparison RESULT COMPARISON --set set-0001 --baseline NAME --out NEW
hop-design construction edit-view RESULT --evaluated --out NEW [--port PORT]
```

Use `--reference OPTION` and repeated `--preserve STAGE:PROPERTY` with the first
form. `--query` is exclusive with stage/focus/reference/preserve flags. The result
may be a saved discovery or molecular edit packet. Browsing keeps the admitted
pool fixed; it performs no new search. Selection rechecks the source and complete
query. The evaluated viewer defaults to the complete route with local supported
choices. `preview-variant` defaults to `--state all`; `atlas` exports the same
recorded route for an explicit option and accepts optional `--focus ADDRESS.json`.
All outputs are create-only. See the
[conditional walkthrough](../guides/explore-conditional-variants.md).

## Molecular edits and exact sequence families

The [folded-sequence guide](../guides/edit-folded-sequences.md) connects these commands:

```text
# Preview a specific molecular edit before evaluating it.
hop-design construction prepare-edit REQUEST --loop WORD --out NEW
hop-design construction prepare-edit REQUEST --placement LEFT_BP:RIGHT_BP --out NEW
hop-design construction preview-edit EDIT.json --out NEW
hop-design construction evaluate-edit EDIT.json --out NEW
hop-design construction select-edit OPTIONS --edit-digest DIGEST --member NAME=OPTION --baseline NAME --out NEW
hop-design construction edit-view REQUEST --out NEW [--port PORT]
hop-design construction preview-sequence-family REQUEST --out NEW
hop-design construction evaluate-sequence-family REQUEST --out NEW
hop-design construction select-sequence-family OPTIONS --member MEMBER=OPTION --baseline MEMBER --out NEW
```

Loop, placement, member, basal-nick and release flags are repeatable. End-word
edits require both `--left-end` and `--right-end`. Every write is create-only.
`edit-view` binds only to loopback and prints a transient local URL; Ctrl+C stops
serving without deleting generated files. Preview does not search; evaluation
retains failed or unexamined choices. Invalid/stale selections return nonzero.

For independently installed consumers, see the
[external command and artifact interface](external-artifacts.md). It documents
JSON reports, runtime identity, file discovery and replay, named methods, and
selected-local construction without requiring Python model imports.

## Substrate spaces

```text
# Preview the finite payload space, compile it and verify saved records.
hop-design space preview SPEC_PATH
hop-design space compile SPEC_PATH --out NEW_DIRECTORY
hop-design verify BUNDLE_DIRECTORY
```

`space preview` accepts a strict `hop/substrate-space/v1` YAML or JSON file,
reports the actual ordered IUPAC domain at each variable position, computes
exact cardinality without enumerating members, and writes nothing. A valid
specification above the tested 256-design release envelope is reported as
`blocked` with exit code zero. Invalid input returns nonzero.

`space compile` re-previews, exhaustively expands, compiles and verifies every
exact member, writes the design-set bundle and review projections in a
sibling temporary directory, and commits the complete package atomically. It
publishes a complete set or no set. Success reports complete, unique, and
duplicate counts before paths, followed by the manifest's claim-status values.

`verify` accepts either a design-set `bundle/` containing `manifest.json` or an
existing single-design bundle containing `hop-bundle.json`. It rejects a
missing or ambiguous root.

## Single designs

```text
hop-design compile (--sequence DNA | --spec FILE)
                   [--out NEW_DIRECTORY] [--design-id ID] [--dry-run]
```

Exactly one input is required. `--sequence` accepts exact or symbolic DNA IUPAC
input. `--spec` accepts a strict `.json`, `.yaml`, or `.yml` file with schema
`hop.design/v2` or `hop.resolved-design/v2`. `--design-id` is sequence-only; if
omitted, HOP derives a stable sequence-based ID. `--out` must not exist.
`--dry-run` performs loading, normalization, validation, checking, resolution,
artifact generation, and digest calculation without writing.
`--out` is optional with `--dry-run`; it remains required for a persisted
compilation.

Success prints the named defaults reference, plan ID, bundle ID, and output
status. Ambiguous input selection, an unsupported extension or schema, invalid
DNA or coordinates, expected infeasibility, an unknown reference, or an
existing target returns a nonzero exit with a boundary-specific message.

## Construction navigation

```text
hop-design construction summary BUNDLE_PATH
hop-design construction list BUNDLE_PATH [OPTIONS]
hop-design construction inspect BUNDLE_PATH
                                (REALIZATION_ID | --ordinal NUMBER | --selection SELECTION_JSON)
                                [--end left|right [--base-index INDEX]]
                                [--out NEW_DIRECTORY [--reason TEXT]]
hop-design construction select BUNDLE_PATH (REALIZATION_ID | --ordinal NUMBER)
                               --out NEW_SELECTION_JSON
hop-design construction portrait BUNDLE_PATH (REALIZATION_ID | --selection SELECTION_JSON)
                                 --out NEW_DIRECTORY
```

These commands consume a verified construction bundle. They do not compile,
rerun, subset, or reseal its result.

`construction portrait` starts with the whole joined hairpin. The exported SVG
shows added paired regions, loop and local sequence detail. Its accompanying
`selection.json` binds the same result and realization as `preparation/oligos.csv`
and the exact route. A release interface is labeled as a later stage; it is not
drawn as an exposed end of the earlier hairpin. A stale selection fails before
any output is published.

`construction summary` reports exact route accounting, geometry, endpoint group
counts, and recorded claim status.

`construction list` defaults to accepted routes grouped by achieved geometry
in canonical replay order. It supports:

- `--status accepted|rejected|truncated|all`;
- `--group-by geometry|product|none` and an exact `--group` key;
- repeatable `--enzyme` filters for accepted routes;
- `--sort canonical|retained-overhead|cleavage-enzyme-count|auxiliary-count|source-length`;
- `--descending`;
- `--full-ids` to show complete route identities and group-filter keys; and
- `--limit 1..1000`, with a default of 25 displayed rows.

Rejected, truncated, and mixed-status listings require `--group-by none`.
Enzyme filters and noncanonical sorts apply only to accepted routes because
rejected and truncated dispositions carry failure evidence rather than a
materialized route. `--limit` changes terminal display only: it never changes
verified accounting, search status, membership, or result identity. Canonical
ordinal is replay metadata, not a rank.
Listings lead with molecular differences and a route number. This number is
the canonical ordinal in that bundle; filtering and sorting do not renumber it.

`construction inspect` prints the exact source ssDNA, required external
materials, molecular-state and transition counts, and endpoint for one accepted
realization. It states whether source-fragment removal has a bound, verified
program; resolving an endpoint alone does not establish that preparation step.
For a released insert, it prints both actual cohesive ends in 5′→3′ order and
their overhang polarity. Earlier
endpoints do not report prospective ends as already generated.

`--end left|right` focuses inspection on one released end: its oriented word,
protruding strand, release-cut boundaries and base-by-base material origins.
`--base-index` selects one position in that end word, starting at zero in its
own 5′→3′ direction; it requires `--end`. Material and product indexes are also
zero-based on their respective 5′→3′ sequences. Each row shows the actual end
base beside its material base, which can be complementary. Material-use identity
keeps distinct roles separate even when their sequence and chemistry match.
An earlier endpoint or invalid end/index is an error, before any output write.
The focus is a text view; `--out` still exports the complete selected trajectory.
Machine consumers use the existing trajectory JSON, not the text's formatting.

`--out` writes `report.md`, `oligos.csv`, and `oligos.fasta`, plus
the exact trajectory JSON and SVG, to a new directory outside the verified input
bundle. `--reason` records the caller's selection rationale in the report only;
it requires `--out` and nonblank text. It does not alter the selection or result.
The realization may be supplied
by exact identity, by `--ordinal` from the same bundle's listing, or through one
result-bound selection file. These selectors are mutually exclusive.

`construction select` writes a new `hop.construction-selection/v1` JSON file.
The reference contains the source result identity and one accepted materialized
realization identity. The complete result and its alternatives remain unchanged.
Loading the selection against a different result fails.
Selection by ordinal stores the resolved full identities, not the display number.
Selection paths must use the exact `.json` extension, and output paths must be
outside the verified input bundle.

## Prepare a product request

`hop-design construction prepare REQUEST [--compare-to REFERENCE] --out DIRECTORY` translates strict
`hop.product-request/v1` JSON/YAML into existing construction and local inputs.
It preserves the authored request and reports required, derived and unresolved
values. `preview.json` includes end footprints, expanded contact permissions,
minimum adapter association and optional reference differences. It does not run
a search or establish feasibility. See the
[construction journey](../guides/design-a-construction.md).

An empty `construction list` now reports result dispositions and examined versus
nominal combinations, along with recorded rejection/truncation reasons and
commands for inspecting all dispositions. A broad code remains broad; it does
not identify a necessary or minimal repair.

## Continue explicit local choices

`hop-design construction continue REQUEST --design-id ID --foldback RESULT_JSON
--foldback-realization-id ID [--basal RESULT_JSON --basal-realization-id ID]
--out DIRECTORY` takes payload, endpoint, hairpin terminal arms and material
policies from the authored request. Local authorities are replayed and checked
against its expanded inputs. Use `construction local-choices RESULT_JSON` to
inspect IDs first; never choose by assumed preference or file order.

A stopped executor preserves `inputs/request.json` and the local inputs. Discover
any still-missing family with `construction discover-local` before continuing.
The command does not silently search or substitute a selection. It returns the
same scoped report and create-only artifacts as `construction execute`.

At the lower seam, `construction compile-local-design --endpoint ssdna_hairpin`
requires both `--hairpin-left-arm` and `--hairpin-right-arm`, each exact DNA
written 5′→3′. These flags and downstream basal evidence cannot be combined;
PCR endpoints derive their component and reject the arm flags.

Complete request reports now expose `preparation_constraints` when the evaluator
identifies an exact failed condition. Read the comparison relation and stage:
a fixed adapter's required prefix is not a proposed replacement whole oligo.

## Compare scaffold families

`construction prepare-family REQUEST --out DIRECTORY` previews a strict
`hop.construction-family/v1` roster without search. `construction execute-family
REQUEST --continuation sole-witness --out DIRECTORY` executes it with every
member's status and coverage retained. `construction select-set REQUEST --out
DIRECTORY` verifies `hop.construction-set/v1` membership and retrieves exact
preparations, baseline comparisons and consolidated order specifications.
See the [family walkthrough](../guides/compare-scaffold-families.md).

`construction compare LEFT RIGHT --left-ordinal N --right-ordinal N --format json`
emits the typed comparison; the default `--format text` retains the human report.
The selectors still address exact accepted members within their own authorities.


## Portable scaffold comparison report

Use `project_construction_family_report` in Python or
`hop-design construction report-family` to turn a saved family into one portable
PDF/SVG report and preparation index. Optional `selection`, `baseline` and explicit
member `edits` preserve user intent without automatic selection or relaxation.
See [the public walkthrough](../guides/compare-scaffold-families.md#open-one-portable-comparison)
and [the report contract](family-report.md) for inputs, verification, outputs and
scope.


`construction author-family BRIEF --out NEW` compiles product, variation, shared
properties and material permissions into a canonical family request and preview.
`construction reconcile-family FAMILY --source-member NAME --outcome OUTCOME
--out NEW [--member NEW_NAME --revised-request FAMILY_JSON] [--preferred-loop-nt N]` verifies an explicit
continuation into a new family. The optional pair declares an edited alternative;
original requests and failures remain in the revision. See the
[family workflow](../guides/compare-scaffold-families.md#reconcile-an-explicit-continuation).


`--preferred-loop-nt N` records a declared reason for the caller's explicit local
choice. The selected completed product must match; omission does not infer a
preference. Recovery reports show the local choices and completed preparation.

`construction match-family FAMILY --reference-member NAME --reference-choice N
--max-continuations N --out NEW` evaluates bounded preparations against a named
complete member. Requirements remain fixed, outcomes and local coverage remain
visible, and selection remains explicit. See the
[matching walkthrough](../guides/compare-scaffold-families.md#find-preparations-that-preserve-the-comparison).


## Complete scaffold options

For a full interface target catalogue, `construction survey evaluate REQUEST
--index FILE --max-evaluations N --local-nodes N --local-realizations N
--release-site-pairs N` creates a checkpoint. Add `--resume` to advance it under
the same bound request, producer and evaluation limits. `--max-checkpoint-bytes`
sets the database capacity (default 1 GiB). `construction survey inspect REQUEST
--index FILE [--offset N --limit N]` lists outcomes and witness addresses.
`--navigation-nodes N` bounds each successor seek; pending positions commit as
navigation-only records with zero molecular continuations. Complete empty basal
proofs retain scoped exclusions across resume without enumerating every free
foldback/source-context combination as a separate molecular attempt.
For the request objective `paired_scaffold_completions`, `--navigation-frontier N`
limits pending work (default 4096, maximum 100000); reaching that bound leaves
coverage unresolved. The objective seeks complete auxiliary handles while
preserving paired scaffold and released-insert choices. It does not enumerate
every exact hairpin or preparation. Both objective and execution limits bind the
checkpoint; see the [scope definitions](interface-survey-search.md#complete-handles-without-enumerating-every-interchangeable-word).

`construction survey verify REQUEST --index FILE` replays all recorded outcomes.
`construction survey upgrade REQUEST --index FILE --source-producer PRODUCER_JSON
--out NEW` replays a **stopped** checkpoint under the installed build. Supply the
exact original producer mapping. It preserves the source, rejects changed results
or continuations, and publishes a new checkpoint plus transition receipt only
after every recorded evaluation matches. `--max-checkpoint-bytes` bounds the new
database. Progress goes to stderr and the final receipt to stdout. This can cost
as much as repeating the saved search; retain the old runtime for rollback.
`construction survey query REQUEST --index FILE [--query PREDICATES]` returns
conditional complete paths and declared values without adding evaluations.
`construction survey select REQUEST --index FILE --target N --step N
--identity MATERIALIZED_ID [--query PREDICATES]` emits an exact query-bound
selection. `construction survey sample REQUEST --index FILE --seed N
[--query PREDICATES]` selects a matching complete preparation deterministically
from the same admitted pool. Save either output as `selection.json`.
`construction survey atlas REQUEST --index FILE --selection selection.json
--out NEW` replays that selection and exports the complete atlas and teaching SVGs.
`construction survey retrieve REQUEST --index FILE --selection selection.json
--out NEW` exports its preparation. `construction survey view REQUEST --index FILE
--out NEW` opens the same query, selection and retrieval semantics through a local
browser server. It does not launch new search or relax the request. See
[interface surveys](../guides/survey-interfaces.md).

- `construction preview-scaffolds REQUEST --out NEW` previews a strict
  `hop.scaffold-discovery/v1` through `/v6` intention and permitted preparation edits.
  Versions 2–5 add terminal translation, required-target scheduling, joint placements
  and molecular parameter restrictions. Version 6 adds an explicit joint
  receiving-end roster; it does not cross independently permitted left/right words.
  See the [schema contracts](schemas.md#product-driven-scaffold-discovery).
- `construction discover-scaffolds REQUEST --out NEW` evaluates its bounded
  branches with all achieved-state requirements retained.
- `construction select-scaffolds OPTIONS --member NAME=OPTION --baseline NAME
  --out NEW` retrieves explicitly named members. Repeat `--member`, `--shared`
  and `--compare` for a deliberate set. See the
  [product-first example](../../examples/scaffold-discovery/README.md).

- `construction explore REQUEST --max-continuations N --out NEW` evaluates a
  bounded prefix of recorded local pairs and returns complete molecules, failed
  continuations, coverage and whole-scaffold PDF/SVG views.
- `construction option-sets OPTIONS COMPARISON --out NEW` finds complete and
  incomplete shared backgrounds for a `hop.scaffold-comparison/v1` request.
- `construction select-options OPTIONS --option LABEL [--option LABEL ...]
  --baseline LABEL --out NEW` retrieves explicit choices. Reuse `--comparison
  COMPARISON` to preserve its roster and controls, or declare repeated `--shared`
  and `--compare` properties. Do not mix these two authoring forms.

All output paths are create-only. Labels belong to the specified options packet.
See [the public workflow](../guides/explore-scaffolds.md).

## Required molecular comparisons

- `construction preview-comparison BRIEF --out DIR` exposes obligations and conflicts.
- `construction execute-comparison BRIEF --out DIR` runs bounded discovery and assessment.
- `construction assess-comparison BRIEF DISCOVERY --out DIR` assesses existing verified options.
- `construction select-comparison RESULT --set LABEL --baseline MEMBER --out DIR` retrieves an explicit set.

See [Specify and retrieve a molecular comparison](../guides/specify-a-comparison.md).
Comparison-brief/v3 adds stage-qualified controls, required-first discovery and
explicit prior-material reuse. Selection preserves those declarations in the
portable construction-set/v2 packet. Earlier request versions retain their
existing search and comparison meanings.
