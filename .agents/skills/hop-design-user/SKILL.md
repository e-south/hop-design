---
name: hop-design-user
description: Discover complete HOP hairpins or inserts from a stem and optional constraints; inspect routes, retrieve oligos, compile designs and verify bundles. Do not use for code changes or lab protocols.
metadata:
  version: 0.8.3
  category: science-workflow
  tags: [hop-design, dna-sequence, compilation, construction]
---

# HOP Design user router

## Scope

Use HOP's public requests to specify molecules and retrieve their preparations.
HOP derives paired arms, junctions and processing states from those requests.

## Start with the user's task

Read the matching reference before acting. Route code changes to the maintainer
skill and wet-lab or interpretive work outside HOP.

| Question | Public surface | Skill reference |
| --- | --- | --- |
| Preserve my stem and discover complete designs, with optional ends | `hop_design.construction.discover_designs` / `hop-design design` | [discovery guide](../../../docs/guides/discover-designs.md) |
| Author advanced scaffold discovery with explicit method catalogs | `hop_design.construction` discovery | [scaffold guide](../../../docs/guides/discover-product-scaffolds.md) |
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

1. Identify the supplied stem and intended product. End words are optional; do not ask for them unless the user needs a particular interface. Inspect the effective permissions, then follow the discovery guide.
2. Use `choices.explain()` or `design query --format text` to distinguish available choices, an empty filter and a scoped exclusion. Offer continuation only when the answer identifies remaining search. Use `--format json` in automation. Stop on invalid inputs or corruption; never relax a requirement silently.
3. Select a complete preparation explicitly, or sample only when requested. Reuse its selection for the route and parts; write exports to new paths and verify at handoff.

## Guardrails

- `payload` is authored once; its paired arm is derived. Expand symbolics only under an explicit bound.
- A substrate-space preview is allocation-free. `blocked` means the valid exhaustive space exceeds its declared bound; it is not infeasible or truncated.
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
## Success Criteria

Distinguish `schema-valid`, `compiled`, `bundle-verified`, `destination-compatible`,
and `experimentally supported`. Digital derivation does not establish physical
construction, QC, activity, yield, or performance.

## Trigger Tests

Use the [route and behavior matrix](references/test-matrix.md) to check routing.

## Progressive Disclosure Resources

- `references/external-sources.md`: source guidance.
