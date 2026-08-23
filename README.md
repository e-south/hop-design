# ![hop — Hairpin Oligonucleotide Processing](assets/hop-design-banner.svg)

[![Checks](https://github.com/e-south/hop-design/actions/workflows/ci.yaml/badge.svg)](https://github.com/e-south/hop-design/actions/workflows/ci.yaml)
[![Python 3.12–3.14](https://img.shields.io/badge/python-3.12%E2%80%933.14-264653)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2a9d8f)](LICENSE)

HOP Design compiles DNA sequences and explicit hairpin-processing mechanics
into checked molecular plans and portable files. Exact and DNA IUPAC sequences
use the same API. The paired payload is always derived.

HOP is alpha software. Its molecular states do not substitute for a laboratory
protocol, measured yield, or an application-specific acceptance profile. HOP
is not published on PyPI.

## Install

Install a versioned wheel from
[GitHub Releases](https://github.com/e-south/hop-design/releases), then verify
the published SHA-256 checksum:

```bash
grep 'hop_design-0.1.0a6-py3-none-any.whl$' SHA256SUMS | shasum -a 256 -c -
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

From a contributor checkout, use `uv run` as shown below. In an environment
with the released wheel installed, omit `uv run`.

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
| Understand payload, foldback, and basal components | [Hairpin concepts](docs/concepts/README.md) |
| Understand bounded junction discovery | [Discovery and selection](docs/concepts/discovery-and-selection.md) |
| Understand the supported physical method | [Processing and assembly](docs/concepts/processing-and-assembly.md) |
| Inspect persisted artifacts | [Design bundle](docs/reference/bundle-layout.md) or [method bundle](docs/reference/method-bundle-layout.md) |
| Navigate every public document | [Documentation map](docs/README.md) |

The CLI provides the common compile path. Discovery, method resolution, and
typed integration use the Python API.

## Boundary

HOP owns generic hairpin geometry, deterministic molecular derivation, and
portable evidence for the products it creates. It does not own workspaces,
runs, observations, application profiles, destination-specific assembly, or
laboratory execution. A restriction product is destination-neutral, not
automatically ready for cloning.

The [architecture](ARCHITECTURE.md), [engineering contracts](DESIGN.md), and
[reliability guarantees](RELIABILITY.md) define maintainer-facing boundaries.

Use [GitHub Issues](https://github.com/e-south/hop-design/issues) for bugs and
feature proposals. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a
pull request. Report vulnerabilities through [SECURITY.md](SECURITY.md), not a
public issue.
