# Contributing to HOP Design

HOP accepts focused changes that preserve its public ownership boundary and
scientific contracts. Start with [docs/index.md](docs/index.md) and the
nearest accepted architecture decision.

## Development loop

```bash
uv sync --locked
uv run pre-commit install
bash ./scripts/agent-preflight --strict
bash ./scripts/agent-verify
```

Add a failing test before changing behavior. Public schema or ownership changes
also require an ADR and updated schema/reference documentation. Generated bundle
digests must change only when the serialized contract changes intentionally.

## Pull requests

Keep pull requests narrow enough to review. Describe the contract affected,
negative-path tests, compatibility impact, and local verification. Main is
protected; changes merge through pull requests after required checks pass.

Do not include private datasets, application-specific identifiers, credentials,
machine-local paths, or output from neighboring repositories. See
[SECURITY.md](SECURITY.md) for vulnerability reports.
