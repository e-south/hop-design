# HOP Design agent router

Load one skill for the task:

- Use HOP: `.agents/skills/hop-design-user/SKILL.md`.
- Change or review HOP: `.agents/skills/hop-maintainer/SKILL.md`.

Load the other only for a repository defect or public-use verification.
## Find the contract
- Product meaning or terminology: `docs/start/mental-model.md` and
  `docs/language/ontology.md`.
- Dependency direction or ownership: `ARCHITECTURE.md` and the relevant record
  under `docs/architecture/decisions/`.
- Validation, derivation, errors, or coordinates: `DESIGN.md` and
  `docs/language/relationships-and-invariants.md`.
- Bundle identity or replay: `RELIABILITY.md` and the matching bundle reference.

## Verify changes
Run targeted checks while editing, then use the scope in
`docs/dev/performance.md#choose-the-verification-boundary`:

- Molecular views, typography, layout or browser interaction only:
  `bash ./scripts/agent-verify --scope presentation` plus visual and molecular-inventory review.
- Molecular rules, requests, discovery, identity, admission or handoff behavior:
  `bash ./scripts/agent-verify --scope source`.
- Packaging, runtime dependencies, publication, CI routing, or an uncertain boundary:
  `bash ./scripts/agent-verify` (full). CI keeps this endpoint before merge,
  except for the exact README/artwork paths documented in the verification guide.

Each scope includes strict preflight. Report the scope actually passed; presentation
is not whole-package verification. Use `--workers 2` when useful; never duplicate gates.
Manuscript-only edits use their owning study's document and artifact checks.

## Repository boundary
Keep public code independent of machine-local paths, private study identities or sequences,
application policy, workspace/run concepts and neighboring repos. Author the payload once; derive its paired arm.
