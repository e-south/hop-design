---
doc_id: hop-quickstart
title: HOP Design quickstart
intent: Compile and verify one exact and one symbolic demonstration design.
audience:
  - new users
owner: HOP Design maintainers
status: active
last_verified: 2026-08-20
---

# Quickstart

From a repository checkout:

```bash
uv sync --locked
uv run hop-design compile --sequence ACGT --design-id exact-demo --out build/exact
uv run hop-design compile --sequence NRY --design-id symbolic-demo --out build/symbolic
```

The CLI prints the named default, plan ID, and bundle ID. It refuses to replace
an existing output directory. Add `--dry-run` to validate and compile without
writing.

A strict JSON or YAML specification uses the same endpoint:

```bash
uv run hop-design compile --spec examples/generic-symbolic.yaml --out build/from-spec
```

Use `hop.design/v1` for the named generic demonstration and
`hop.resolved-design/v1` when foldback, basal, terminal-nick, and optional
release events have already been resolved by the caller.

In Python:

```python
import hop_design as hop

spec = hop.create_spec(sequence="NRY", design_id="symbolic-python-demo")
report = hop.check(spec)
report.raise_for_errors()
compilation = hop.compile(spec)
compilation.write("build/symbolic-python")
hop.verify_bundle("build/symbolic-python")
```

The generic route builds `basal left + payload + foldback junction + derived
paired payload + basal right`. It exists to exercise the software contracts and
must not be interpreted as a wet-lab protocol or experimental validation.
