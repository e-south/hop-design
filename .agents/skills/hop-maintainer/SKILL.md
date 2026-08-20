---
name: hop-maintainer
description: Implement, refactor, review, or release HOP Design code, schemas, contracts, bundles, CLI/API, docs, tests, packaging, CI, and agent guidance. Do not use for routine compilation, wet-lab protocols, or downstream work.
metadata:
  version: 0.1.0
  category: engineering
  tags: [hop-design, contract-first, test-driven-development]
---

# HOP Design maintainer workflow

Preserve one authority per derivation and one dependency direction. The public
package is deterministic and public-by-construction.

## Scope

Change or review this repository's product contracts and implementation. Keep
caller-owned application, execution, evidence, and larger-construct semantics
outside HOP.

## Success Criteria

- A failing test proves the missing behavior before implementation.
- The smallest owning layer changes and all affected contracts remain explicit.
- Targeted checks and the full deterministic verification endpoint pass.
- Documentation, schemas, and public/private boundaries agree with the code.

## Workflow

1. Read `ARCHITECTURE.md`, `DESIGN.md`, `RELIABILITY.md`, `SECURITY.md`, the
   relevant ADR, and `docs/dev/plans/roadmap.md` as the change requires; then
   inspect the worktree.
2. State one observable behavior and its nearest test level.
3. RED: add the smallest failing test and confirm the intended failure.
4. GREEN: implement the minimum behavior through the owning layer. Do not add
   speculative abstractions, hidden defaults, or compatibility aliases.
5. REFACTOR: improve names and structure only while the focused test stays green.
6. Run the smallest relevant suite, then:

   ```bash
   bash ./scripts/agent-preflight --strict
   bash ./scripts/agent-verify
   ```

7. Inspect the diff for generated paired inputs, unsafe paths, private data,
   dependency inversions, undocumented schema changes, and stale docs.

## Required Deliverables

- RED evidence and focused GREEN verification.
- Changed ownership boundary and contract surface.
- Full `agent-verify` evidence, including source-versus-wheel parity.
- Updated owning docs or ADR for any semantic or architectural change.
- Explicitly deferred downstream work and remaining roadmap phase.

## Guardrails

- Public models remain strict, frozen, and `extra="forbid"`.
- The payload is authored once. Paired payloads and physical output sequences
  are derived.
- Exact and symbolic DNA IUPAC paths remain first-class and share the facade.
- Coordinate meanings are explicit; do not interchange boundaries, counts,
  indexes, and base-pair counts.
- Unknown schemas/catalogs and corrupt state raise. Expected infeasibility uses
  stable diagnostics.
- New enumeration has a hard bound and a truthful completion status.
- `models` imports no higher layer. Lower layers do not import design/API/CLI.
- No runtime import from a caller repository and no workspace, run, observation,
  evidence, assay, or larger-construct ownership in the core.
- A private parity translator stays outside this repository and is temporary.
- Do not create a remote, remove the publication brake, publish, or add
  credentials without explicit release authorization.

## Trigger Tests

Read `references/test-matrix.md` for positive, near-miss, and negative routing
cases before changing this skill's description.

## Output Contract

Report the behavior changed, RED evidence, implementation boundary, focused and
full verification evidence, remaining roadmap phase, and any downstream work
that was intentionally not touched.

## Progressive Disclosure Resources

- Routing cases: `references/test-matrix.md`.
- External engineering sources: `references/external-sources.md`.
