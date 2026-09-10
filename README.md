# ![hop — Hairpin Oligonucleotide Processing](assets/hop-design-banner.svg)

[![Python 3.12–3.14](https://img.shields.io/badge/python-3.12%E2%80%933.14-264653)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2a9d8f)](LICENSE)

Design a DNA hairpin construction around the sequence you want to study.
HOP keeps that payload unchanged and searches the surrounding sequence for
junctions compatible with your enzymes and requested product.

Define one payload sequence or a pattern of fixed and degenerate bases. Preview
the implied sequence space, compile paired designs, or search the foldback and
basal neighborhoods for arrangements compatible with your enzymes and limits.

For a supported construction request, inspect the source oligo, adapter and
primers when required, and the molecular steps leading to your endpoint.
Require a particular product end or leave its sequence open within stated
bounds. A complete construction must satisfy the material and processing
requirements together; a possible local junction alone is not enough.
These are sequence and processing specifications, not predictions of
laboratory success.

## Start here

- [Install and compile a first design](docs/guides/quickstart.md).
- [Define and preview a substrate space](docs/guides/substrate-spaces.md).
- [Search junctions and compile a construction](docs/guides/compile-construction.md).
- [Understand the molecular steps and limits](docs/start/mental-model.md).

The [documentation](docs/index.md) covers sequence input, bounded searches,
material specifications, molecular views, and file/API reference.

## Availability

HOP is alpha software; APIs and file formats may change before 1.0. Install
[v0.1.0a8](https://github.com/e-south/hop-design/releases/tag/v0.1.0a8) from
GitHub Releases, not PyPI, and use its
[tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a8).
This checkout also contains unreleased construction-search features; see
[capabilities and limits](docs/dev/plans/roadmap.md#source-capabilities).

## Help and contribution

Report bugs through [GitHub Issues](https://github.com/e-south/hop-design/issues)
and vulnerabilities through [SECURITY.md](SECURITY.md). For development, start
with [CONTRIBUTING.md](CONTRIBUTING.md); coding agents use
[AGENTS.md](https://github.com/e-south/hop-design/blob/main/AGENTS.md).
