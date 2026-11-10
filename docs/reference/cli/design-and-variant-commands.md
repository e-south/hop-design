# Design discovery and variant commands

Resolve complete designs, inspect conditional alternatives, or compile an authored
design or substrate space. Command placeholders stand for caller sequences and paths;
output directories must be new.

Return to the [cli reference](../cli.md).

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
[edition guide](../../guides/share-atlas-edition.md) for input bindings and scope.

`--left` and `--right` are optional exact end constraints for a released insert.
`--context` chooses a versioned context or context file. Use molecular flags or a
request file, not both. `hairpin` and `adapter_ligated_hairpin` request their actual
hairpin endpoints without release requirements. Continue resumes discovery under
the same permissions. For hairpins, `--first-choices N` stops after N new complete
preparations or the evaluation limit; it selects nothing and retains failed
attempts. Each hairpin call examines at most 64 local pairs; subsequent calls retain
the earlier snapshots. Start with the
[complete-design tutorial](../../guides/discover-designs.md).

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
[API contract](../python-api/discovery.md#discover-complete-designs) for this optional preference.

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
The [loop comparison example](../../guides/discover-designs/require-comparative-preparations.md#compare-loops-while-holding-the-scaffold)
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
[conditional walkthrough](../../guides/explore-conditional-variants.md).

## Molecular edits and exact sequence families

The [folded-sequence guide](../../guides/edit-folded-sequences.md) connects these commands:

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
[external command and artifact interface](../external-artifacts.md). It documents
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
