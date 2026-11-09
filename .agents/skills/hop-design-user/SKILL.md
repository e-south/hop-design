---
name: hop-design-user
description: Discover complete HOP hairpins or inserts from a stem and optional constraints; inspect routes, retrieve oligos, compile designs and verify bundles. Do not use for code changes or lab protocols.
metadata:
  version: 0.8.4
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
| What does a molecular feature or search result mean? | Terms, measurements and search coverage | [concept index](../../../docs/language/ontology.md) |
| Author advanced scaffold discovery with explicit method catalogs | `hop_design.construction` discovery | [scaffold guide](../../../docs/guides/discover-product-scaffolds.md) |
| What exact designs are in this bounded substrate space? | `hop_design.spaces` | [design](references/design.md) |
| What design does this payload encode? | `hop_design` | [design](references/design.md) |
| What exact construction routes follow from one strict source and verified design? | `hop_design.construction` | [construction](references/construction.md) |
| Which bounded candidates are compatible? | `hop_design.discovery` | [discovery](references/discovery.md) |
| What exact product follows from a named method? | `hop_design.methods` | [methods](references/methods.md) |
| How can I inspect already-derived state? | `hop_design.views` | [views](references/views.md) |
| How do I verify or hand off an artifact? | matching verifier | [verification and integration](references/verification-and-integration.md) |

Read `docs/start/mental-model.md` for the construction steps and how its regions
fit together. Use the concept index above to locate definitions and measurements.

## Workflow

1. Identify the supplied stem and intended product. End words are optional; do not ask for them unless the user needs a particular interface. Inspect the effective permissions, then follow the discovery guide.
2. Use `choices.explain()` or `design query --format text` to distinguish available choices, an empty filter and a scoped exclusion. Offer continuation only when the answer identifies remaining search. Use `--format json` in automation. Stop on invalid inputs or corruption; never relax a requirement silently.
3. Select a complete preparation explicitly, or sample only when requested. Reuse its selection for the route and parts; write exports to new paths and verify at handoff.

## Guardrails

- `payload` is authored once; its paired arm is derived. Expand symbolic sequences only under an explicit bound.
- A substrate-space preview is allocation-free. `blocked` means the valid exhaustive space exceeds its declared bound; it is not infeasible or truncated.
- A hairpin design set contains replay-verified members of an exhaustively compiled substrate space.
- Preserve deterministic order, report geometry measurements, and record caller selection separately from compatibility.
- A design derivation describes calculated anatomy; construction routes and named methods record ordered molecular states.
- Preserve typed statuses exactly. Construction-specific authority and projection rules live in its reference.
- Typed view JSON is the visual authority; rendering cannot derive new state.
- Check a restriction product against the caller's destination, orientation, and assembly ends.
- Do not add private sequences, study identifiers, or caller policies to public examples.

## Required Deliverables

- For an explanation, define the term at its molecular stage and link its reference.
- For a computation, report the operation, input type, exact status, counts, bounds and diagnostics.
- Include relevant result/bundle IDs, new output paths or write-free state, and verification outcome.
## Success Criteria

Report `schema-valid`, `compiled`, `bundle-verified`, `destination-compatible`,
and `experimentally supported` separately, using the responsible owner's records
for each status.

## Trigger Tests

Use the [route and behavior matrix](references/test-matrix.md) to check routing.

## Progressive Disclosure Resources

- `references/external-sources.md`: source guidance.
