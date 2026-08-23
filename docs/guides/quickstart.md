---
doc_id: hop-quickstart
title: HOP Design quickstart
intent: Compile and verify one exact and one symbolic demonstration design.
audience:
  - new users
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
---

# Quickstart

Download a versioned wheel and `SHA256SUMS` from
[GitHub Releases](https://github.com/e-south/hop-design/releases), verify the
wheel's checksum, and install it into a Python 3.12–3.14 environment. HOP is not
published on PyPI.

```bash
grep 'hop_design-0.1.0a6-py3-none-any.whl$' SHA256SUMS | shasum -a 256 -c -
uv venv --python 3.12
source .venv/bin/activate
uv pip install ./hop_design-0.1.0a6-py3-none-any.whl
hop-design compile --sequence ACGT --design-id exact-demo --out build/exact
```

From a contributor checkout:

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
`hop.resolved-design/v1` when foldback and basal components are supplied by the
caller. Omit the terminal nick for route-neutral component assembly; include it
for resolved processing events. A release event requires the resolved route.

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

The CLI intentionally exposes the common compile path. Continue in Python for:

- [bounded geometry discovery concepts](../concepts/discovery-and-selection.md);
- [named processing-method concepts](../concepts/processing-and-assembly.md); or
- [verified consumer integration](../spec-plan-bundle.md).
