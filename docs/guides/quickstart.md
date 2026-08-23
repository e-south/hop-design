---
doc_id: hop-quickstart
title: HOP Design quickstart
intent: Compile and verify one exact and one symbolic demonstration design.
audience:
  - new users
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: tutorial
journey:
  - install
  - compile
  - verify
---

# Quickstart

This page targets the unreleased v0.1.0a7 source checkout. The latest
published wheel is v0.1.0a6 and uses the preceding schema generation; use its
[tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a6)
when operating the wheel.

Download a versioned wheel and `SHA256SUMS` from
[GitHub Releases](https://github.com/e-south/hop-design/releases), verify the
wheel's checksum, and install it into a Python 3.12–3.14 environment. HOP is not
published on PyPI.

```bash
# macOS
grep 'hop_design-0.1.0a6-py3-none-any.whl$' SHA256SUMS | shasum -a 256 -c -
# Linux
grep 'hop_design-0.1.0a6-py3-none-any.whl$' SHA256SUMS | sha256sum -c -
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

The release-wheel command above uses the a6 contract shipped with that wheel.
The contributor-checkout commands below exercise the unreleased a7 source
candidate. In the current source candidate, use `hop.design/v2` for the named generic demonstration and
`hop.resolved-design/v2` when foldback and basal components are supplied by the
caller. A design spec records deterministic design derivation, not a laboratory
chronology. A resolved release projection requires explicit terminal-nick
geometry; complete production history belongs to a named method request.

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

The generic design derivation builds `basal left + payload + foldback junction + derived
paired payload + basal right`. It exists to exercise the software contracts and
must not be interpreted as a wet-lab protocol or experimental validation.

The CLI intentionally exposes the common compile path. Continue in Python with:

- [a bounded basal-candidate query](discover-compatible-basal-candidates.md);
- [a named processing-method bundle](resolve-production-method.md); or
- [verified consumer integration](../provenance/overview.md).
