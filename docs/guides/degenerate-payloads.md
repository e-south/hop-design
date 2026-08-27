---
doc_id: hop-degenerate-payloads
title: Symbolic DNA IUPAC payloads
intent: Explain exact versus degenerate semantics and expansion safety.
audience:
  - users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
doc_type: how-to
journey:
  - compile
---

# Symbolic DNA IUPAC payloads

The supported alphabet is `ACGTRYSWKMBDHVN`. Lowercase and formatting
whitespace normalize to uppercase; empty input, RNA `U`, punctuation, digits,
and other symbols fail immediately.

`hop.compile(sequence="ACGT")` creates an `ExactPayload`.
`hop.compile(sequence="NRY")` creates a `DegeneratePayload`. Its paired arm is
the symbolic reverse complement `RYN`. The plan and FASTA retain those symbols.

Compilation does not expand a symbolic payload. Concrete variants require the
separate explicit operation:

```python
import hop_design as hop

record = hop.PayloadRecord(
    record_id="variants",
    payload=hop.DegeneratePayload(sequence="NR"),
)
expanded = hop.expand_payload(record, max_variants=8)
print(expanded.cardinality)  # 8
```

HOP calculates cardinality before allocating variants. If it exceeds
`max_variants`, `VariantBudgetExceededError` exposes both values and no partial
result is returned. Variant IDs and ordering are deterministic.
