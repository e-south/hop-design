# HOP Design agent router

Use this file to find the owning source. Do not restate scientific contracts in
prompts or generated plans when a linked document already owns them.

## Route by task

- Explain HOP, compile an exact or symbolic sequence, or inspect a bundle:
  read `.agents/skills/hop-design-user/SKILL.md`.
- Change code, schemas, architecture, documentation, packaging, or release
  behavior: read `.agents/skills/hop-maintainer/SKILL.md`.
- Learn the ontology and product boundary: read `docs/ontology.md` and
  `docs/spec-plan-bundle.md`.
- Change dependency direction or ownership: read `ARCHITECTURE.md` and the
  relevant record under `docs/architecture/decisions/` first.
- Change validation, derivation, errors, or coordinates: read `DESIGN.md` and
  `docs/contracts.md` first.
- Change bundle identity, writing, or verification: read `RELIABILITY.md` and
  `docs/reference/bundle-layout.md` first.

## Deterministic endpoints

```bash
bash ./scripts/agent-preflight --strict
bash ./scripts/agent-verify
```

Run targeted tests during development. Run `agent-verify` before declaring a
change complete. CI invokes the same endpoint.

## Repository boundary

HOP Design is standalone and public-by-construction. Do not add machine-local
paths, private study identifiers or sequences, application-specific catalogs,
workspace/run abstractions, or runtime imports from neighboring repositories.
Generated paired payload arms are outputs and must never become independently
authored inputs.
