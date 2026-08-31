---
doc_id: hop-method-bundle-layout
title: Method bundle layout and verification
intent: Define the persisted artifacts for one complete hairpin-processing method plan.
audience:
  - bundle consumers
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-22
doc_type: reference
---

# Method bundle layout and verification

A method bundle records how one strict request resolves into modeled molecular
states and products. It is not a design bundle and does not claim that a
restriction product is compatible with a destination, physically constructed,
or recovered. Replay verifies the digital derivation only.

| File | Meaning |
| --- | --- |
| `method-request.json` | Exact authored method request |
| `method-plan.json` | Complete compiler-derived molecular-state plan |
| `method-trajectory.json` | Renderer-independent eight-state view |
| `method-trajectory.svg` | Deterministic rendering of the typed view |
| `hairpin-pcr-duplex.fasta` | Top and bottom strands of the PCR duplex |
| `hairpin-pcr-duplex.gb` | Linear dsDNA GenBank representation with plan-derived features |
| `restriction-product.fasta` | Primary and complementary strands whose plan also records both exact cohesive ends |
| `hairpin-encoding.fasta` | Oriented one-dimensional encoding projection |
| `method-bundle.json` | Content-addressed root manifest |

`compile_linear_source_method_bundle(request)` requires a complete method
resolution. `MethodCompilation.write(path)` writes to a sibling temporary
directory, verifies it, and atomically renames it without replacing an existing
path.

`load_verified_method_bundle(path)` rejects unsafe or unmanifested paths,
missing or modified files, noncanonical JSON, inconsistent root digests, and
unknown schemas. It then recompiles `method-request.json` and requires the plan,
all eight exported artifacts, manifest, and bundle ID to match byte for byte.
Updating checksums after altering a derived file does not satisfy this replay.

The manifest records `hairpin_encoding_digest`. A caller may join a method
product to a design object only when the method request supplied
`expected_hairpin_encoding`, or when the handoff explicitly compares this
digest with the design encoding's `sequence_digest`. The bundles retain
separate identities.
