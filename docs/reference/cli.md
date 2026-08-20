---
doc_id: hop-cli-reference
title: HOP Design CLI reference
intent: Document current commands, options, output, and exit behavior.
audience:
  - CLI users
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# CLI reference

```text
hop-design compile (--sequence DNA | --spec FILE) --out NEW_DIRECTORY
                   [--design-id ID] [--dry-run]
```

Exactly one input is required. `--sequence` accepts exact or symbolic DNA IUPAC
input. `--spec` accepts a strict `.json`, `.yaml`, or `.yml` file with schema
`hop.design/v1` or `hop.resolved-design/v1`. `--design-id` is sequence-only; if
omitted, HOP derives a stable sequence-based ID. `--out` must not exist.
`--dry-run` performs loading, normalization, validation, checking, resolution,
artifact generation, and digest calculation without writing.

Success prints the named defaults reference, plan ID, bundle ID, and output
status. Ambiguous input selection, an unsupported extension or schema, invalid
DNA or coordinates, expected infeasibility, an unknown reference, or an
existing target returns a nonzero exit with a boundary-specific message.
