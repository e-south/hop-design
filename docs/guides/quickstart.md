---
doc_id: hop-quickstart
title: HOP Design quickstart
intent: Compile and verify one exact and one symbolic demonstration design.
audience:
  - new users
owner: HOP Design maintainers
status: active
last_verified: 2026-09-08
doc_type: tutorial
journey:
  - install
  - compile
  - verify
---

# Quickstart

This page describes the published v0.1.0a8 artifact. Use the release's
[tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a8)
when operating that immutable artifact.

Download a versioned wheel and `SHA256SUMS` from
[GitHub Releases](https://github.com/e-south/hop-design/releases), verify the
wheel's checksum, and install it into a Python 3.12–3.14 environment. HOP is not
published on PyPI.

```bash
# macOS
grep 'hop_design-0.1.0a8-py3-none-any.whl$' SHA256SUMS | shasum -a 256 -c -
# Linux
grep 'hop_design-0.1.0a8-py3-none-any.whl$' SHA256SUMS | sha256sum -c -
uv venv --python 3.12
source .venv/bin/activate
uv pip install ./hop_design-0.1.0a8-py3-none-any.whl
hop-design compile --sequence ACGT --design-id exact-demo --out build/exact
```

The command prints the design and saved-file identifiers. Open the output
directory to inspect the sequence and feature files.

## Preview a sequence space

From a source checkout, run the included small verification fixture:

```bash
uv sync --locked
uv run hop-design space preview examples/fixed-site-three-base-context.yaml
uv run hop-design space compile examples/fixed-site-three-base-context.yaml \
  --out build/fixed-site-three-base-context
uv run hop-design verify build/fixed-site-three-base-context/bundle
```

The example defines 64 exact designs from three variable paired positions.
Open `build/fixed-site-three-base-context/review.html` to inspect the paired
sequences and download their CSV, FASTA, and SVG files. Preview calculates the
space size without creating files. The [substrate-space guide](substrate-spaces.md)
explains how to define a different pattern and interpret the compilation limit.

## Specify one design

```bash
uv run hop-design compile --sequence ACGT --design-id exact-demo --out build/exact
uv run hop-design compile --sequence NRY --design-id symbolic-demo --out build/symbolic
```

The CLI refuses to replace an existing output directory. Add `--dry-run` to derive the
design and check its constraints without writing; `--out` is not required for
that read-only call.

A strict JSON or YAML specification uses the same endpoint:

```bash
uv run hop-design compile --spec examples/generic-symbolic.yaml --out build/from-spec
```

Use `hop.design/v2` for the named generic example and `hop.resolved-design/v2`
when you supply the foldback and basal components. See the
[design language](../language/overview.md) for those inputs.

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

This compiles hairpin anatomy with a derived complementary payload arm. It
does not specify a construction procedure or establish experimental success.

## Continue

- [Load payload records](payload-sources-and-expansion.md).
- [Search basal candidates](discover-compatible-basal-candidates.md) or
  [compile a construction](compile-construction.md) through Python.
- [Check a named method](resolve-production-method.md) and
  [render molecular views](render-component-views.md).

The CLI can also inspect and select saved constructions with
`hop-design construction`. Construction search and compilation use Python;
check the [construction guide](compile-construction.md) for source-only features
not available in the published release.
