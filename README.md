# ![hop — Hairpin Oligonucleotide Processing](assets/hop-design-banner.svg)

[![Checks](https://github.com/e-south/hop-design/actions/workflows/ci.yaml/badge.svg)](https://github.com/e-south/hop-design/actions/workflows/ci.yaml)
[![Python 3.12–3.14](https://img.shields.io/badge/python-3.12%E2%80%933.14-264653)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2a9d8f)](LICENSE)

HOP Design compiles authored DNA payloads and explicit molecular events into
checked, portable Hairpin Oligonucleotide Processing design bundles. Exact and
DNA IUPAC payloads use the same API. Paired payloads are always derived.

HOP is alpha software. The included direct-synthesis route is a synthetic
software demonstration, not a laboratory protocol or an experimentally
supported application profile. Package metadata blocks PyPI upload until a
separate release decision is recorded.

## Install for development

```bash
git clone https://github.com/e-south/hop-design.git
cd hop-design
uv sync --locked
```

No PyPI distribution is published. The supported installation surface is the
GitHub source repository until the release gate is opened.

## Five-minute path

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
print(compilation.plan.final_insert.sequence)
compilation.write("build/demo-python")
```

HOP preserves ambiguity symbols. It never silently expands, truncates, or
selects a concrete variant. Explicit expansion and typed design spaces require
cardinality budgets before allocation.

## What HOP owns

- strict `Spec -> Plan -> Bundle` compilation;
- exact and symbolic payload ingestion and bounded variant generation;
- foldback, basal-junction, nick, release, and strand-state contracts;
- deterministic JSON, FASTA, typed view, SVG, digest, and provenance artifacts.

HOP does not own workspaces, runs, observations, evidence stores, private
application profiles, or laboratory execution.

## Documentation and support

Start with the [documentation map](docs/README.md). The
[architecture](ARCHITECTURE.md), [design contracts](DESIGN.md), and
[reliability guarantees](RELIABILITY.md) define maintainer-facing boundaries.

Use [GitHub Issues](https://github.com/e-south/hop-design/issues) for bugs and
feature proposals. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a
pull request. Report vulnerabilities through [SECURITY.md](SECURITY.md), not a
public issue.
