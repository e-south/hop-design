---
doc_id: hop-cli-reference
title: HOP Design CLI reference
intent: Document current commands, options, output, and exit behavior.
audience:
  - CLI users
owner: HOP Design maintainers
status: active
last_verified: 2026-08-27
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
specification above its declared `max_members` is reported as `blocked` with
exit code zero. `max_members` must be between 1 and the current implementation
ceiling of 100,000. Invalid input returns nonzero.

`space compile` re-previews, exhaustively expands, compiles and verifies every
exact member, writes the design-set authority and human projections in a
sibling temporary directory, and commits the complete package atomically. It
never publishes an authoritative partial set. Success reports complete,
unique, and duplicate counts before paths, followed by the same downstream
non-evidence recorded in the manifest.

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
