---
doc_id: hop-cli-reference
title: HOP Design CLI reference
intent: Document current commands, options, output, and exit behavior.
audience:
  - CLI users
owner: HOP Design maintainers
status: active
last_verified: 2026-09-08
doc_type: reference
---

# CLI reference

## Substrate spaces

```text
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
exact member, writes the design-set authority and human projections in a
sibling temporary directory, and commits the complete package atomically. It
never publishes an authoritative partial set. Success reports complete,
unique, and duplicate counts before paths, followed by the same downstream
evidence boundary recorded in the manifest.

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
--out is optional with `--dry-run`; it remains required for a persisted
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
                                [--out NEW_DIRECTORY [--reason TEXT]]
hop-design construction select BUNDLE_PATH (REALIZATION_ID | --ordinal NUMBER)
                               --out NEW_SELECTION_JSON
```

These commands consume a verified construction bundle. They do not compile,
rerun, subset, or reseal its result.

`construction summary` reports exact route accounting, geometry and endpoint
group counts, and the experimental evidence boundary.

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
realization. `--out` writes `report.md`, `oligos.csv`, and `oligos.fasta`, plus
the exact trajectory JSON and SVG, to a new directory outside the verified input
bundle. `--reason` records the caller's selection rationale in the report only;
it requires `--out` and nonblank text. It does not alter the selection or result.
The realization may be supplied
by exact identity, by `--ordinal` from the same bundle's listing, or through one
result-bound selection file. These selectors are mutually exclusive.

`construction select` writes a new `hop.construction-selection/v1` JSON file.
The reference contains the source result identity and one accepted materialized
realization identity. It records caller intent; it does not endorse the route,
delete alternatives, or become evidence of physical construction. Loading it
against a different result fails.
Selection by ordinal stores the resolved full identities, not the display number.
Selection paths must use the exact `.json` extension, and output paths must be
outside the verified input bundle.
