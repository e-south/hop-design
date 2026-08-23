# ![hop — Hairpin Oligonucleotide Processing](assets/hop-design-banner.svg)

[![Checks](https://github.com/e-south/hop-design/actions/workflows/ci.yaml/badge.svg)](https://github.com/e-south/hop-design/actions/workflows/ci.yaml)
[![Python 3.12–3.14](https://img.shields.io/badge/python-3.12%E2%80%933.14-264653)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2a9d8f)](LICENSE)

HOP is a domain-specific language and compiler for sequence-encoded hairpins.
It turns declared hairpin anatomy into a deterministic encoding and can
separately resolve named production methods into exact, destination-neutral
molecular products. Exact and DNA IUPAC sequences use the same design API.

HOP is alpha software. Its molecular states do not substitute for a laboratory
protocol, measured yield, or an application-specific acceptance profile. HOP
is not published on PyPI.
The latest wheel is v0.1.0a6. Main and these docs describe unreleased v0.1.0a7
source contracts; use the [v0.1.0a6 docs](https://github.com/e-south/hop-design/tree/v0.1.0a6) with that wheel.

## Install

Install a versioned wheel from
[GitHub Releases](https://github.com/e-south/hop-design/releases), then verify
the published SHA-256 checksum:

```bash
# macOS
grep 'hop_design-0.1.0a6-py3-none-any.whl$' SHA256SUMS | shasum -a 256 -c -
# Linux
grep 'hop_design-0.1.0a6-py3-none-any.whl$' SHA256SUMS | sha256sum -c -
uv venv --python 3.12
source .venv/bin/activate
uv pip install ./hop_design-0.1.0a6-py3-none-any.whl
hop-design --help
```

For development:

```bash
git clone https://github.com/e-south/hop-design.git
cd hop-design
uv sync --locked
```

## Compile a design

From a contributor checkout, use `uv run` as shown. With the released a6 wheel,
only the `--sequence` form below applies; omit `uv run` and follow its tagged docs.

```bash
uv run hop-design compile \
  --sequence NRYNRY \
  --design-id demo-symbolic \
  --out build/demo-symbolic

uv run hop-design compile \
  --spec examples/generic-symbolic.yaml \
  --out build/from-spec
```

```python
import hop_design as hop

compilation = hop.compile(sequence="NRYNRY", design_id="demo-symbolic")
print(compilation.plan.hairpin_encoding_insert.sequence)
compilation.write("build/demo-python")
```

HOP preserves ambiguity symbols. It never silently expands, truncates, or
selects a concrete variant. Explicit expansion and typed design spaces require
cardinality budgets before allocation.

## Choose a path

| Task | Start here |
| --- | --- |
| Install, compile, and verify a design | [Quickstart](docs/guides/quickstart.md) |
| Understand HOP's five separate claims | [Mental model](docs/start/mental-model.md) |
| Learn payload, foldback, and basal primitives | [Design language](docs/language/overview.md) |
| Run a bounded compatibility query | [Discovery guide](docs/guides/discover-compatible-basal-candidates.md) |
| Resolve and verify a named production method | [Method guide](docs/guides/resolve-production-method.md) |
| Verify identity, replay, and handoffs | [Provenance and verification](docs/provenance/overview.md) |
| Inspect persisted artifacts | [Design bundle](docs/reference/bundle-layout.md) or [method bundle](docs/reference/method-bundle-layout.md) |
| Position HOP in a larger design ecosystem | [Ownership boundaries](docs/ecosystem/ownership-boundaries.md) |
| Navigate every public document | [Documentation map](docs/index.md) |

The CLI provides compilation; discovery, methods, and integration use Python.

## Boundary

HOP owns hairpin meaning, deterministic molecular derivation, named molecular
transformations, and portable verification artifacts. It does not own workspaces,
runs, observations, application profiles, destination-specific assembly, or
laboratory execution. A restriction product is destination-neutral, not
automatically ready for cloning.

The [architecture](ARCHITECTURE.md), [engineering contracts](DESIGN.md), and
[reliability guarantees](RELIABILITY.md) define maintainer-facing boundaries.

Use [GitHub Issues](https://github.com/e-south/hop-design/issues) for bugs and feature proposals.
Read [CONTRIBUTING.md](CONTRIBUTING.md); report vulnerabilities through [SECURITY.md](SECURITY.md).
