# ![hop — Hairpin Oligonucleotide Processing](assets/hop-design-banner.svg)

[![Python 3.12–3.14](https://img.shields.io/badge/python-3.12%E2%80%933.14-264653)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2a9d8f)](LICENSE)

Define a DNA payload—an exact sequence or a pattern of fixed and degenerate
bases—and find the surrounding sequence needed for a hairpin construction.
HOP keeps that payload unchanged while searching foldback and basal junctions
compatible with your enzymes and requested product. Inspect the source oligo,
adapter, primers, and modeled processing steps; compare selected constructions
before choosing one. These are sequence and processing specifications, not
predictions of laboratory success.

## Start here

- [Install and compile a first design](docs/guides/quickstart.md).
- [Preview a substrate space](docs/guides/substrate-spaces.md).
- [Search junctions and compile a construction](docs/guides/compile-construction.md).
- [Understand the molecular steps and limits](docs/start/mental-model.md).

[All guides and API reference](docs/index.md).

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
