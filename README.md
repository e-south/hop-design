# ![hop — Hairpin Oligonucleotide Processing](assets/hop-design-banner.svg)

[![Checks](https://github.com/e-south/hop-design/actions/workflows/ci.yaml/badge.svg)](https://github.com/e-south/hop-design/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/e-south/hop-design/graph/badge.svg)](https://codecov.io/gh/e-south/hop-design)
[![Python 3.12–3.14](https://img.shields.io/badge/python-3.12%E2%80%933.14-264653)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2a9d8f)](LICENSE)

HOP helps scientists describe a DNA hairpin, calculate the sequence that must
pair with it, and check whether a supported way of making it fits the design.
It produces exact, verifiable design and method records; it does not predict
whether a laboratory experiment will succeed.

| Project status | Current contract |
| --- | --- |
| Maturity | HOP is alpha software; schemas and public APIs may change before 1.0. |
| Published release | [v0.1.0a6](https://github.com/e-south/hop-design/releases/tag/v0.1.0a6), with its [tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a6). |
| Source line | Main and this documentation describe unreleased v0.1.0a7. |
| Distribution | Release artifacts are published through [GitHub Releases](https://github.com/e-south/hop-design/releases), not PyPI. |

## Choose a route

| Goal | Start here |
| --- | --- |
| Decide whether the problem belongs in this domain | [Mental model](docs/start/mental-model.md) |
| Install a release and compile a first design | [Quickstart](docs/guides/quickstart.md) |
| Begin with payloads or a bounded payload library | [Payload-first guide](docs/guides/payload-sources-and-expansion.md) |
| Find compatible candidates under explicit limits | [Discovery guide](docs/guides/discover-compatible-basal-candidates.md) |
| Resolve an exact named production method | [Method guide](docs/guides/resolve-production-method.md) |
| Render typed foldback or basal views | [Component-view guide](docs/guides/render-component-views.md) |
| Verify bundles and compare a design/method handoff | [Provenance and verification](docs/provenance/overview.md) |
| Place or assess a product downstream | [Ownership boundaries](docs/ecosystem/ownership-boundaries.md) |
| Navigate concepts, guides, reference, and maintenance | [Documentation map](docs/index.md) |

The CLI covers common design compilation. Discovery, named methods, typed
views, and integration use the Python surfaces documented by each route.

## Claim boundary

A compiled encoding establishes deterministic design derivation. A verified
method bundle establishes replay of one named molecular method. Neither claim
establishes empirical cleavage efficiency, destination compatibility,
laboratory yield, or experimental success. A restriction product is
destination-neutral until a downstream system evaluates a destination.

## Project routes

- Coding agents start with [AGENTS.md](AGENTS.md), which selects a focused user
  or maintainer skill without loading both workflows.
- Contributors use [CONTRIBUTING.md](CONTRIBUTING.md) and the maintainer-facing
  [architecture](ARCHITECTURE.md), [design contracts](DESIGN.md), and
  [reliability guarantees](RELIABILITY.md).
- Report bugs and proposals through [GitHub Issues](https://github.com/e-south/hop-design/issues).
  Report vulnerabilities through [SECURITY.md](SECURITY.md).
