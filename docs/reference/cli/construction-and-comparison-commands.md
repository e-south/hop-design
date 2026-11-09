# Construction and comparison commands

Read verified construction bundles, prepare or continue requests, and retrieve explicit
comparisons or survey preparations. Command placeholders stand for caller files and
identities; output paths are create-only.

Return to the [cli reference](../cli.md).

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

These commands read a saved construction bundle and verify it before navigation.
Use them to inspect its results and explicitly select a recorded route. They do
not compile, rerun, subset, or reseal its result.

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
[construction journey](../../guides/design-a-construction.md).

An empty `construction list` reports how evaluated combinations were classified,
the examined and nominal combination counts, recorded rejection/truncation reasons and
commands for inspecting all dispositions. A broad rejection code does not
identify which requirement must change or the smallest change that would make
the construction work.

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
See the [family walkthrough](../../guides/compare-scaffold-families.md).

`construction compare LEFT RIGHT --left-ordinal N --right-ordinal N --format json`
emits the typed comparison; the default `--format text` retains the human report.
The selectors still address exact accepted members within their own authorities.


## Portable scaffold comparison report

Use `project_construction_family_report` in Python or
`hop-design construction report-family` to turn a saved family into one portable
PDF/SVG report and preparation index. Optional `selection`, `baseline` and explicit
member `edits` preserve user intent without automatic selection or relaxation.
See [the public walkthrough](../../guides/compare-scaffold-families.md#open-one-portable-comparison)
and [the report contract](../family-report.md) for inputs, verification, outputs and
scope.


`construction author-family BRIEF --out NEW` compiles product, variation, shared
properties and material permissions into a canonical family request and preview.
`construction reconcile-family FAMILY --source-member NAME --outcome OUTCOME
--out NEW [--member NEW_NAME --revised-request FAMILY_JSON] [--preferred-loop-nt N]` verifies an explicit
continuation into a new family. The optional pair declares an edited alternative;
original requests and failures remain in the revision. See the
[family workflow](../../guides/compare-scaffold-families.md#reconcile-an-explicit-continuation).


`--preferred-loop-nt N` records a declared reason for the caller's explicit local
choice. The selected completed product must match; omission does not infer a
preference. Recovery reports show the local choices and completed preparation.

`construction match-family FAMILY --reference-member NAME --reference-choice N
--max-continuations N --out NEW` evaluates bounded preparations against a named
complete member. Requirements remain fixed, outcomes and local coverage remain
visible, and selection remains explicit. See the
[matching walkthrough](../../guides/compare-scaffold-families.md#find-preparations-that-preserve-the-comparison).


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
checkpoint; see the [scope definitions](../interface-survey-search/molecular-domain-and-completion.md#complete-handles-without-enumerating-every-interchangeable-word).

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
[interface surveys](../../guides/survey-interfaces.md).

- `construction preview-scaffolds REQUEST --out NEW` previews a strict
  `hop.scaffold-discovery/v1` through `/v6` intention and permitted preparation edits.
  Versions 2–5 add terminal translation, required-target scheduling, joint placements
  and molecular parameter restrictions. Version 6 adds an explicit joint
  receiving-end roster; it does not cross independently permitted left/right words.
  See the [schema contracts](../schemas/discovery-and-selection-packets.md#product-driven-scaffold-discovery).
- `construction discover-scaffolds REQUEST --out NEW` evaluates its bounded
  branches with all achieved-state requirements retained.
- `construction select-scaffolds OPTIONS --member NAME=OPTION --baseline NAME
  --out NEW` retrieves explicitly named members. Repeat `--member`, `--shared`
  and `--compare` for a deliberate set. See the
  [product-first example](../../../examples/scaffold-discovery/README.md).

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
See [the public workflow](../../guides/explore-scaffolds.md).

## Required molecular comparisons

- `construction preview-comparison BRIEF --out DIR` exposes obligations and conflicts.
- `construction execute-comparison BRIEF --out DIR` runs bounded discovery and assessment.
- `construction assess-comparison BRIEF DISCOVERY --out DIR` assesses existing verified options.
- `construction select-comparison RESULT --set LABEL --baseline MEMBER --out DIR` retrieves an explicit set.

See [Specify and retrieve a molecular comparison](../../guides/specify-a-comparison.md).
Comparison-brief/v3 adds stage-qualified controls, required-first discovery and
explicit prior-material reuse. Selection preserves those declarations in the
portable construction-set/v2 packet. Earlier request versions retain their
existing search and comparison meanings.
