---
name: hop-maintainer
description: Change or review HOP code, schemas, APIs, docs, tests, packaging, CI, or releases. Do not use for routine compilation, lab protocols, or downstream applications.
metadata:
  version: 0.1.2
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
- Targeted checks and the verification scope appropriate to the changed responsibility pass.
- Full source and installed-distribution verification passes before merge or release,
  except for the documented README/artwork-only merge gate.
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
6. Run the smallest relevant suite, then the matching scope:

   ```bash
   bash ./scripts/agent-verify --scope presentation  # molecular views and browser only
   bash ./scripts/agent-verify --scope source        # molecular/API/search/handoff changes
   bash ./scripts/agent-verify                      # source + installed distribution
   ```

   Choose one boundary; these are not three commands to run in sequence. Each
   includes strict preflight. Packaging, runtime dependencies, uncertain scope,
   CI routing and release require the full gate. Merge uses that gate except for
   the exact README/artwork paths documented in the verification guide.
   A presentation-only change requires
   rendered review and conserved molecular content as well as its focused gate.
   See `docs/dev/performance.md#choose-the-verification-boundary` for the
   responsibility map and bounded worker option.

7. Inspect the diff for generated paired inputs, unsafe paths, private data,
   dependency inversions, undocumented schema changes, and stale docs.

## Required Deliverables

- RED evidence and focused GREEN verification.
- Changed ownership boundary and contract surface.
- The named scope, its result and exact changed responsibility. Include
  source-versus-wheel parity for a full merge/release verification; do not imply
  that a presentation or source pass established installed-package parity.
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
verification scope and evidence, remaining roadmap phase, and any downstream work
that was intentionally not touched.

## Progressive Disclosure Resources

- Routing cases: `references/test-matrix.md`.
- External engineering sources: `references/external-sources.md`.
