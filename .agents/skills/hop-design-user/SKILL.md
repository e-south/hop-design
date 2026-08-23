---
name: hop-design-user
description: Use HOP Design to load or expand payloads, run bounded discovery, compile design or named-method bundles, render typed views, and verify handoffs. Do not use for code changes, lab protocols, private biology, or generic sequence analysis.
metadata:
  version: 0.5.0
  category: science-workflow
  tags: [hop-design, dna-sequence, compilation]
---

# HOP Design user workflow

Use the deterministic HOP API as the authority. Never invent a paired arm,
junction, route, or application constraint outside a typed contract.

## Scope

Operate the existing public API, CLI, models, and bundles. Explain only the
scientific state actually represented by those contracts. Read
`docs/start/mental-model.md`, `docs/language/ontology.md`, and
`docs/provenance/overview.md` for terms, the matching guide
or reference document for the requested operation, and `RELIABILITY.md` or
`SECURITY.md` for integrity or safety claims.

## Success Criteria

- The requested HOP operation uses the public deterministic surface.
- Exact versus symbolic state, diagnostics, IDs, and verification are explicit.
- No private input, unsupported biological claim, or independent paired arm is
  introduced.

## Workflow

1. Identify the requested product: a design bundle, bounded discovery result,
   named-method result or bundle, typed view, or verified consumer handoff.
2. Read the matching concept and reference document. Confirm whether the input
   may be DNA IUPAC or must be exact DNA; do not reinterpret RNA, punctuation,
   an empty value, or a malformed file as DNA.
3. For a design bundle, use the public facade:

   ```python
   import hop_design as hop

   compilation = hop.compile(sequence="NRY", design_id="example")
   ```

4. For a reproducible design path, create or load a strict `HopSpec` or
   `ResolvedHopSpec`, call `hop.check(spec)`, and stop on errors before
   compilation. Use explicit mechanics requests and caller-owned policy; do not
   invent private catalog entries.
5. For discovery, create the smallest strict request and hard bounds that answer
   the question. Report candidate-space size, completion or truncation, the
   canonical ordinal, and caller-owned selection separately. Import bounded
   query operations and contracts from `hop_design.discovery`.
6. For the implemented physical method, require exact molecular inputs and use
   `methods.compile_linear_source_multinick_hairpin_pcr(request)` from
   `hop_design.methods` (imported as `methods`). Use
   `methods.compile_linear_source_method_bundle(request)` only after the result is
   complete. State the transformation-based method ID; do not substitute a
   design-derivation identifier.
7. Before any write, state which bundle type will be created and confirm that
   the target path does not exist. Verify the matching bundle before
   interpreting its files:

   ```python
   import hop_design as hop

   bundle_manifest = hop.verify_bundle("build/example")
   verified_design = hop.load_verified_bundle("build/example")
   ```

   For a verified method handoff, use `methods.verify_method_bundle(path)` to
   verify its raw manifest and `methods.load_verified_method_bundle(path)` to load the verified
   request, plan, and product.
8. For integration, branch on product type. For a verified design handoff, pass the
   `load_verified_bundle()` result's `plan.hairpin_encoding_insert`, its
   `sequence_digest`, and nested features. For a verified method handoff, pass the
   `load_verified_method_bundle()` result's
   `plan.restriction_digest_product`, request, plan, cut geometry, and
   `bundle.hairpin_encoding_digest`. The consumer must explicitly compare that
   digest with `verified_design.plan.hairpin_encoding_insert.sequence_digest`.
   Do not invent
   nested features on a restriction product, let a consumer rederive HOP
   geometry, or call a destination-neutral product assembly-ready.
9. Report the input kind, operation or method ID, plan and bundle IDs when
   applicable, output path or dry-run state, and diagnostics. Keep scientific
   claims within the resolved contract.

## Required Deliverables

- Operation, product type, and input kind.
- Method, plan, and bundle identifiers when applicable.
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
- Treat `canonical_ordinal` as reproducible ordering, never as a biological or
  procurement recommendation. An optimization claim requires a named objective,
  reported measurements, and a deterministic tie-breaker.
- Treat recognition-site placement as sequence-and-cut geometry, not evidence
  of empirical cleavage efficiency.
- Treat typed view JSON as the scientific view contract. Renderers cannot
  recompute molecular state.
- Do not describe a design derivation as a wet-lab protocol or infer application
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
