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
---

# Bundle layout and verification

| File | Meaning |
| --- | --- |
| `hop-spec.json` | Canonical expanded authored intent |
| `hop-plan.json` | Fully resolved immutable plan and lock |
| `provenance.json` | Deterministic compiler and reference provenance |
| `hairpin-encoding.fasta` | Generated one-dimensional hairpin-encoding sequence |
| `source-oligo.fasta` | Actual resolved-route input when it differs from the hairpin encoding |
| `hop-bundle.json` | Root manifest and neutral external references |

Resolved-mechanics bundles add the following content-addressed artifacts:

| File | Meaning |
| --- | --- |
| `expected-intermediates.json` | Foldback and basal evaluations plus optional released strand state |
| `foldback-view.json` / `.svg` | Typed foldback QA view and deterministic rendering |
| `basal-view.json` / `.svg` | Typed basal terminal-nick view and deterministic rendering |
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
