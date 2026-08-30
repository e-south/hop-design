# HOP Design agent router

Use this file only to select the owning workflow. Load one skill first; follow
its progressive-disclosure references as the task requires.

## Choose one skill

| Requested work | Load |
| --- | --- |
| Explain or use the design language, payload-centered construction, discovery, named methods, typed views, bundle verification, or immutable handoffs | `.agents/skills/hop-design-user/SKILL.md` |
| Change or review code, schemas, architecture, documentation, tests, packaging, CI, or releases | `.agents/skills/hop-maintainer/SKILL.md` |

Do not load both skills for routine work. Cross the boundary only when a user
operation exposes a repository defect or a maintainer change needs public
dogfood evidence.

## Escalate to an authority

- Product meaning or terminology: `docs/start/mental-model.md` and
  `docs/language/ontology.md`.
- Dependency direction or ownership: `ARCHITECTURE.md` and the relevant record
  under `docs/architecture/decisions/`.
- Validation, derivation, errors, or coordinates: `DESIGN.md` and
  `docs/language/relationships-and-invariants.md`.
- Bundle identity or replay: `RELIABILITY.md` and the matching bundle reference.

## Verification endpoints

Run targeted checks while editing. Before declaring a repository change
complete, run `bash ./scripts/agent-preflight --strict` and
`bash ./scripts/agent-verify`; CI invokes the same full endpoint.

## Repository boundary

Keep public code and examples independent of machine-local paths, private study
identities or sequences, application policy, workspace/run concepts, and
neighboring repositories. The payload is authored once; its paired arm remains
derived.
