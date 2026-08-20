---
name: hop-design-user
description: Use HOP Design to load/expand payloads, plan bounded spaces, evaluate mechanics, compile specs, render views, and verify bundles. Do not use for code changes, lab protocols, private biology, or generic sequence analysis.
metadata:
  version: 0.2.0
  category: science-workflow
  tags: [hop-design, dna-sequence, compilation]
---

# HOP Design user workflow

Use the deterministic HOP API as the authority. Never invent a paired arm,
junction, route, or application constraint outside a typed contract.

## Scope

Operate the existing public API, CLI, models, and bundles. Explain only the
scientific state actually represented by those contracts. Read
`docs/ontology.md` and `docs/spec-plan-bundle.md` for terms, the matching guide
or reference document for the requested operation, and `RELIABILITY.md` or
`SECURITY.md` for integrity or safety claims.

## Success Criteria

- The requested HOP operation uses the public deterministic surface.
- Exact versus symbolic state, diagnostics, IDs, and verification are explicit.
- No private input, unsupported biological claim, or independent paired arm is
  introduced.

## Workflow

1. Identify the requested operation: explain, load payloads, expand variants,
   plan a bounded design space, evaluate mechanics, create/check a spec,
   compile, render, write, inspect, or verify.
2. Confirm the input is an exact or DNA-IUPAC sequence. Do not reinterpret RNA,
   punctuation, an empty value, or a malformed file as DNA.
3. For the common path, use the public facade:

   ```python
   import hop_design as hop

   compilation = hop.compile(sequence="NRY", design_id="example")
   ```

4. For a reproducible path, create or load a strict `HopSpec` or
   `ResolvedHopSpec`, call `hop.check(spec)`, and stop on errors before
   compilation. Use explicit mechanics requests and caller-owned policy; do not
   invent private catalog entries.
5. Before writing, state that the built-in route is the visible
   `generic-direct-synthesis@1` software demonstration and that the target path
   must not exist.
6. Verify a written bundle before interpreting its files:

   ```python
   import hop_design as hop

   bundle = hop.verify_bundle("build/example")
   ```

7. Report the normalized payload kind, plan ID, bundle ID, output path or dry-run
   state, and any diagnostics. Keep scientific claims within the plan.

## Required Deliverables

- Operation and input kind.
- Plan and bundle identifiers when compilation succeeds.
- Output path and bundle verification status when files are written.
- Diagnostics, invalid-state errors, and scientific limitations.

## Guardrails

- The input term is `payload`: explain it as “the input sequence to be paired.”
- Use `foldback junction` and `basal junction` for physical parts. Do not expose
  migration-only aliases as public schema terms.
- A symbolic payload remains symbolic during check and compile. Expand only
  through `hop.expand_payload` with an explicit hard budget; never sample,
  truncate, or choose one representative sequence.
- Calculate design-space cardinality before interpreting rows. Do not bypass
  `max_designs`, silently drop combinations, or render every bundle merely to
  review the space.
- Keep physical foldback/basal/release derivation separate from caller
  eligibility and application policy. A reserve basal profile compiles only
  with explicit reserve acceptance.
- Treat typed view JSON as the scientific view contract. Renderers cannot
  recompute molecular state.
- Do not describe the generic route as a wet-lab protocol or infer application
  fitness from successful compilation.
- Do not add private sequences, study identifiers, or caller profiles to the
  repository or examples.
- Do not mutate a spec, output directory, or external record without the
  caller's requested operation and a validated preview.

## Trigger Tests

Read `references/test-matrix.md` for positive, near-miss, and negative routing
cases before changing this skill's description.

## Output Contract

Return the operation performed, authoritative IDs, exact artifact path when one
was written, verification status, and diagnostics or limitations. Distinguish
“schema-valid,” “compiled,” “bundle-verified,” and “experimentally supported.”
They are not interchangeable claims.

## Progressive Disclosure Resources

- Routing cases: `references/test-matrix.md`.
- Skill-authoring evidence: `references/external-sources.md`.
