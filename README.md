# ![hop — Hairpin Oligonucleotide Processing](assets/hop-design-banner.svg)

[![Checks](https://github.com/e-south/hop-design/actions/workflows/ci.yaml/badge.svg)](https://github.com/e-south/hop-design/actions/workflows/ci.yaml)
[![codecov](https://codecov.io/gh/e-south/hop-design/graph/badge.svg)](https://codecov.io/gh/e-south/hop-design)
[![Python 3.12–3.14](https://img.shields.io/badge/python-3.12%E2%80%933.14-264653)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-2a9d8f)](LICENSE)

Specify the duplex context you want to test. HOP returns the complete paired
hairpin designs and a stable handoff for construction and measurement. It does
not predict whether a laboratory experiment will succeed.

The first journey is `question → substrate rule → exact paired designs → CSV,
FASTA, generic projections, and verified handoff`. HOP previews bounded spaces
without allocation and compiles every member in deterministic order. The tool
does not choose a biological target or publication example; application and
figure decisions remain with the study that consumes the design package.

No physical construction, QC, or activity record is attached.

| Project status | Current contract |
| --- | --- |
| Maturity | HOP is alpha software; schemas and public APIs may change before 1.0. |
| Published release | [v0.1.0a7](https://github.com/e-south/hop-design/releases/tag/v0.1.0a7), with its [tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a7). |
| Source line | The unreleased v0.1.0a8 candidate contains the construction-contract v5 cutover; use tagged v0.1.0a7 documentation with the published wheel. |
| Distribution | Release artifacts are published through [GitHub Releases](https://github.com/e-south/hop-design/releases), not PyPI. |

## Choose a route

| Goal | Start here |
| --- | --- |
| Define, preview, and compile a bounded substrate space | [Substrate-space guide](docs/guides/substrate-spaces.md) |
| Decide whether the problem belongs in this domain | [Mental model](docs/start/mental-model.md) |
| Install a release and compile a first design | [Quickstart](docs/guides/quickstart.md) |
| Load payload records or use advanced composable axes | [Payload-source guide](docs/guides/payload-sources-and-expansion.md) |
| Find compatible candidates under explicit limits | [Discovery guide](docs/guides/discover-compatible-basal-candidates.md) |
| Find multi-nick programs that create an exact fragment partition | [Source-partition guide](docs/guides/discover-source-partitions.md) |
| Compile one strict payload-centered construction route | [Construction guide](docs/guides/compile-construction.md) |
| Resolve an exact named production method | [Method guide](docs/guides/resolve-production-method.md) |
| Render typed foldback or basal views | [Component-view guide](docs/guides/render-component-views.md) |
| Verify bundles and compare a design/method handoff | [Provenance and verification](docs/provenance/overview.md) |
| Place or assess a product downstream | [Ownership boundaries](docs/ecosystem/ownership-boundaries.md) |
| Navigate concepts, guides, reference, and maintenance | [Documentation map](docs/index.md) |

`hop_design.spaces` is the scientist-facing facade. The package root
`hop_design` and the sibling `hop_design.construction`,
`hop_design.discovery`, `hop_design.methods`, and `hop_design.views` facades are
specialist surfaces for single-design derivation, complete construction,
bounded searches, named methods, and typed projections. They are not required
for the first substrate-space journey.

Construction questions are not one global optimizer. Foldback geometry, basal
geometry, route-level source partitioning, and downstream endpoint
materialization are separate bounded competencies. HOP preserves every valid
result in canonical order; a study chooses which route to test.

Construction v5 resolves PCR endpoint auxiliaries through explicit `derive`,
`constrain`, or `fixed` policies and consumes selected replay-verified source
partitions in complete routes. It adds no thermodynamic rank or hidden handle;
concise grouped CLI navigation remains open product work.

## Claim boundary

A compiled encoding establishes deterministic design derivation. A verified
construction bundle establishes deterministic local discovery, bounded digital
route composition, and its exact `complete`, `infeasible`, or `truncated`
status and accounting. A verified method bundle establishes replay of one named
molecular method. None of these claims establishes empirical cleavage
efficiency, destination compatibility, laboratory yield, or experimental
success. A restriction product is destination-neutral until a downstream
system evaluates a destination.

## Project routes

- Coding agents working in the repository start with
  [AGENTS.md](https://github.com/e-south/hop-design/blob/main/AGENTS.md), which
  selects a focused user or maintainer skill without loading both workflows.
- Contributors use [CONTRIBUTING.md](CONTRIBUTING.md) and the maintainer-facing
  [architecture](ARCHITECTURE.md), [design contracts](DESIGN.md), and
  [reliability guarantees](RELIABILITY.md).
- Report bugs through [GitHub Issues](https://github.com/e-south/hop-design/issues) and vulnerabilities through [SECURITY.md](SECURITY.md).
