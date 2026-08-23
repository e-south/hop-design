---
doc_id: hop-adr-0009
title: ADR 0009 - Paired stem extensions
intent: Represent variable non-payload stem context without weakening payload or basal-junction contracts.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-21
doc_type: decision
---

# ADR 0009: Paired stem extensions

## Context

Some supplied hairpins contain paired sequence between the terminal basal
junction and the payload stem. That sequence can be variable in length and can
contain an intentional mismatch. Calling the whole region a payload would move
non-payload sequence into the application input. Calling it a basal junction
would erase the four-position S3/S2/S1/S0 processing boundary.

## Decision

`ResolvedHopSpec` accepts one optional `PairedStemExtensionRequest`. It contains
literal left and right arms of equal nonzero length and an explicit G:T wobble
choice. HOP derives one antiparallel pair observation per position and records
Watson-Crick, G:T wobble, and hard-mismatch counts.

When present, the compiled insert order is:

```text
basal left
paired-stem-extension left
payload
foldback junction
derived paired payload
paired-stem-extension right
basal right
```

The payload complement remains derived from the authored payload. The extension
arms are literal because an inherited or hand-designed extension may contain an
intentional noncanonical pair. The basal junction remains the separate terminal
four-position profile used by the current processing contract.

## Compatibility

The field is optional and excluded from serialized specs and routes when
absent. Existing five-part inputs and their serialized surfaces remain
unchanged. Plans that contain an extension add two feature roles and one
`stem_extension_pairing` state transition. Consumers must use the plan feature
order rather than assuming that every insert has five parts.

## Consequences

Variable paired stem context is visible in the plan, pair calls, spans, and
content identity. It no longer needs to be hidden in payload metadata or
application flanks. This decision does not create a general sequence-assembly
language; it adds one hairpin-specific optional component observed in supplied
designs.
