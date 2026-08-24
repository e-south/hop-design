---
name: hop-design-user
description: Use HOP Design to load or expand payloads, run bounded discovery, compile design or named-method bundles, render typed views, and verify handoffs. Do not use for code changes, lab protocols, private biology, or generic sequence analysis.
metadata:
  version: 0.6.0
  category: science-workflow
  tags: [hop-design, dna-sequence, compilation]
---

# HOP Design user router

Use HOP as the authority for hairpin meaning. Never invent a paired arm,
junction, route, or destination constraint outside a typed contract.

## Choose one competency

Read only the matching reference before acting.

| Question | Public surface | Skill reference |
| --- | --- | --- |
| What design does this payload encode? | `hop_design` | [design](references/design.md) |
| Which bounded candidates are compatible? | `hop_design.discovery` | [discovery](references/discovery.md) |
| What exact product follows from a named method? | `hop_design.methods` | [methods](references/methods.md) |
| How can I inspect already-derived state? | `hop_design.views` | [views](references/views.md) |
| How do I verify or hand off an artifact? | matching verifier | [verification and integration](references/verification-and-integration.md) |

Read `docs/start/mental-model.md` when the request crosses two or more of these
questions. Read the formal `docs/language/ontology.md` only for architecture or
terminology disputes.

## Shared workflow

1. Name the requested competency, product, and input kind.
2. Use the documented facade and the smallest strict request that answers the
   question.
3. Stop on validation errors, infeasibility, unavailability, truncation, or
   corruption. Do not reinterpret one state as another.
4. Before a write, name the bundle type and require a new target path. After a
   write, run the matching verifier before interpreting artifacts.
5. Report operation, authoritative IDs, input kind, output path or dry-run
   state, verification status, diagnostics, and non-claims.

## Guardrails

- `payload` means the input sequence to be paired. Its paired arm is derived.
- A symbolic payload remains symbolic until explicit, bounded expansion.
- Physical pair classification, caller acceptance policy, and candidate
  selection are separate claims.
- `canonical_ordinal` is deterministic order, not a biological score.
- Recognition-site geometry does not establish empirical cleavage efficiency.
- A design derivation is not a laboratory chronology. Only a named method owns
  ordered molecular states.
- Typed view JSON is the visual authority; rendering cannot derive new state.
- A restriction product is destination-neutral, not assembly-ready.
- Do not add private sequences, study identifiers, or caller policies to public
  examples.

## Output contract

Distinguish `schema-valid`, `compiled`, `bundle-verified`,
`destination-compatible`, and `experimentally supported`. They are not
interchangeable claims.

## Routing tests and sources

- [Positive, near-miss, and negative routes](references/test-matrix.md).
- [Skill-authoring sources](references/external-sources.md).
