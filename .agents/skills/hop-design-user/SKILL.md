---
name: hop-design-user
description: Use HOP to preview spaces, compile designs or construction routes, run discovery or methods, render views, and verify handoffs. Do not use for code changes, lab protocols, private biology, or generic sequence analysis.
metadata:
  version: 0.8.0
  category: science-workflow
  tags: [hop-design, dna-sequence, compilation, construction]
---

# HOP Design user router

Use HOP as the authority for hairpin meaning. Never invent a paired arm,
junction, route, or destination constraint outside a typed contract.

## Scope

Use this skill for public HOP design, construction, discovery, method, view,
verification, and handoff operations. Route repository changes to the
maintainer skill and wet-lab or interpretive work outside HOP.

## Success Criteria

- Use the narrow public facade that owns the claim.
- Report typed status, accounting, identities, and verification without reinterpretation.
- Keep writes create-only and verify authorities before handoff.
- Keep digital results separate from physical construction, QC, activity, compatibility, yield, and performance.

## Choose one competency

Read only the matching reference before acting.

| Question | Public surface | Skill reference |
| --- | --- | --- |
| What exact designs are in this bounded substrate space? | `hop_design.spaces` | [design](references/design.md) |
| What design does this payload encode? | `hop_design` | [design](references/design.md) |
| What exact construction routes follow from one strict source and verified design? | `hop_design.construction` | [construction](references/construction.md) |
| Which bounded candidates are compatible? | `hop_design.discovery` | [discovery](references/discovery.md) |
| What exact product follows from a named method? | `hop_design.methods` | [methods](references/methods.md) |
| How can I inspect already-derived state? | `hop_design.views` | [views](references/views.md) |
| How do I verify or hand off an artifact? | matching verifier | [verification and integration](references/verification-and-integration.md) |

Read `docs/start/mental-model.md` when a request crosses competencies. Read
`docs/language/ontology.md` only for architecture or terminology disputes.

## Workflow

1. Name the competency, product, and input kind.
2. Use its documented facade and smallest strict request.
3. Stop on validation errors, infeasibility, unavailability, truncation, or corruption.
4. Before writing, name the bundle type and require a new path; verify again at handoff.
5. Report the operation, IDs, status, accounting, path or dry run, diagnostics, and non-claims.

## Guardrails

- `payload` is authored once; its paired arm is derived. Expand symbolics only under an explicit bound.
- A substrate-space preview is allocation-free. `blocked` means the valid
  exhaustive space exceeds its declared bound; it is not infeasible or truncated.
- A hairpin design set is a verified digital package, not a physical library.
- Keep deterministic order separate from scoring, geometry from enzyme performance, and selection from compatibility.
- A design derivation is not chronology; construction routes and named methods own their respective ordered molecular states.
- Preserve typed statuses exactly. Construction-specific authority and projection rules live in its reference.
- Typed view JSON is the visual authority; rendering cannot derive new state.
- A restriction product is destination-neutral, not assembly-ready.
- Do not add private sequences, study identifiers, or caller policies to public examples.

## Required Deliverables

- Competency, public operation, and strict input kind.
- Relevant authority IDs, exact status, accounting, bounds, and diagnostics.
- New output path or write-free state, plus verification outcome.
- Claim boundary separating digital derivation from downstream evidence.

## Output Contract

Distinguish `schema-valid`, `compiled`, `bundle-verified`,
`destination-compatible`, and `experimentally supported`.

## Trigger Tests

Use [the route and behavior matrix](references/test-matrix.md).

## Progressive Disclosure Resources

- `references/design.md`, `references/construction.md`, `references/discovery.md`
- `references/methods.md`, `references/views.md`, `references/verification-and-integration.md`
- `references/test-matrix.md`, `references/external-sources.md`
