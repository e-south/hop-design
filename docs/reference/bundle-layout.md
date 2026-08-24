---
doc_id: hop-bundle-layout
title: HOP bundle layout and verification
intent: Define artifact meanings and the content-integrity procedure.
audience:
  - bundle consumers
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-21
doc_type: reference
---

# Bundle layout and verification

| File | Meaning |
| --- | --- |
| `hop-spec.json` | Canonical expanded authored intent |
| `hop-plan.json` | Fully resolved immutable design derivation and lock |
| `provenance.json` | Deterministic compiler and reference provenance |
| `hairpin-encoding.fasta` | Generated one-dimensional hairpin-encoding sequence |
| `source-oligo.fasta` | Resolved-junction input when it differs from the hairpin encoding |
| `hop-bundle.json` | Root manifest and neutral external references |

Explicit component or resolved-junction bundles add these content-addressed artifacts:

| File | Meaning |
| --- | --- |
| `expected-intermediates.json` | Foldback and basal evaluations plus an optional release projection |
| `foldback-view.json` / `.svg` | Route-neutral folded-junction view or source/resolved/folded QA view |
| `basal-view.json` / `.svg` | Route-neutral basal-pairing view or explicit terminal-nick view |
| `released-workflow-view.json` / `.svg` | Optional released-product lineage view and deterministic rendering |

Call `hop_design.load_verified_bundle(path)` to obtain the typed spec, plan,
provenance, manifest, and immutable artifact mapping. It validates the manifest
schema, safe paths, presence, symlink status, size,
artifact digests, absence of unmanifested files, spec/plan root digests,
manifest digest, and derived bundle ID. It then validates the spec, plan, and
provenance schemas, cross-checks their identities and lock references, and
regenerates encoding/source FASTA from the plan. Finally, it recompiles the stored
spec and requires the replayed plan, complete artifact set, and manifest to be
byte-equivalent to the bundle. Digest resealing cannot substitute a different
valid spec for the authored intent that produced the plan.
`verify_bundle(path)` runs the same complete verification and returns only the
root manifest for callers that do not need the typed bundle contents.

This layout records design compilation. A complete production-method plan uses
the separate [method bundle layout](method-bundle-layout.md), joined by the
exact hairpin-encoding sequence digest.
