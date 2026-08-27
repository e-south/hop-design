---
doc_id: hop-design-set-layout
title: Hairpin design-set package and verification
intent: Define the canonical collection authority and regenerable scientist-facing projections.
audience:
  - bundle consumers
  - users
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-27
doc_type: reference
journey:
  - compile
  - verify
---

# Hairpin design-set package and verification

## Question answered

Did one bounded substrate-space specification produce a complete,
deterministically ordered set of verified exact digital hairpin designs?

## Package layout

```text
<destination>/
├── bundle/
│   ├── spec.json
│   ├── manifest.json
│   └── members/<member-id>/
├── source.yaml
├── designs.csv
├── sequences.fasta
└── review.html
```

Only `bundle/` is authoritative. `spec.json` contains the normalized ordered
per-position DNA domains and resolved versioned hairpin defaults reference.
It excludes display names, descriptive context, segment labels, equivalent
segment boundaries, and execution bounds. `manifest.json` uses
`hop.hairpin-design-set/v2` and records exact cardinality, complete coverage,
canonical enumeration order, member assignments, member-bundle paths and
identities, final-encoding digests, the closed claim-status matrix, and a
complete recursive artifact inventory. Each unique member directory is an
unchanged verified `HopBundle`.

The source YAML, CSV, FASTA, and self-contained HTML are regenerable
projections. Editing or regenerating them does not change design-set identity.

## Invariants and identity

Variable positions are traversed from 5-prime to 3-prime. Each IUPAC domain is
filtered through `A`, `C`, `G`, `T` order. `canonical_ordinal` records this
replay order; it is not a score or recommendation. Complete coverage requires
one manifest record per theoretical assignment. Duplicate final encodings
reference the first canonical member; only unique encodings own member bundle
directories.

The canonical specification digest follows the molecular domain vector and
fixed hairpin context. Equivalent molecular rules therefore keep the same
space digest, member identities, bundle bytes, and design-set identifier even
when presentation metadata or a permissive allocation bound changes. The
design-set identifier is derived from the manifest digest without embedding a
display name. Every file below `bundle/` except `manifest.json` is inventoried
by path, byte count, media type, and SHA-256 digest.

The claim-status matrix records complete space accounting, replay-verified
digital designs, method and destination questions that were not evaluated,
and construction, quality-control, and activity evidence that was not
recorded. The offline review renders these values from the verified manifest.

## Operations and failure semantics

`compile_space` stages a new destination, verifies every member, verifies the
collection, writes projections, and renames the complete directory atomically.
A blocked space, failed member, corrupt collection, or existing destination
leaves no committed output.

This release supports exhaustive compilation up to `max_members=100000`.
Preview remains symbolic and reports spaces above a lower submitted bound as
blocked; no streaming or authoritative partial set is available.

`load_verified_design_set` rejects missing, symlinked, modified,
unmanifested, noncanonical, or path-unsafe content. It recomputes the
collection identity, replays the symbolic expansion, and calls
`load_verified_bundle` for every unique member.

Verification establishes complete digital derivation and replay. It does not
establish a production method, destination fit, physical construction,
molecule-level complement fidelity, QC, folding behavior, or biological
activity.
