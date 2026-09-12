---
doc_id: hop-install
title: Install HOP
intent: Choose a released wheel or source checkout and set up HOP for use.
audience: [new users]
owner: HOP Design maintainers
status: active
last_verified: 2026-09-10
doc_type: how-to
journey: [install]
---

# Install HOP

Use Python 3.12–3.14. The commands below use
[uv](https://docs.astral.sh/uv/getting-started/installation/).
Choose a released wheel for the tagged guides or a source checkout for the
construction-search examples.

HOP is alpha software; APIs and file formats may change before 1.0.

## Released package

Download the wheel and `SHA256SUMS` from
[v0.1.0a8](https://github.com/e-south/hop-design/releases/tag/v0.1.0a8).
HOP is not published on PyPI. Run these commands from the download directory,
using the checksum command for your operating system:

```bash
# macOS
grep 'hop_design-0.1.0a8-py3-none-any.whl$' SHA256SUMS | shasum -a 256 -c -
# Linux
grep 'hop_design-0.1.0a8-py3-none-any.whl$' SHA256SUMS | sha256sum -c -
```

Continue only if the checksum matches:

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install ./hop_design-0.1.0a8-py3-none-any.whl
hop-design --help
```

Use the release's
[tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a8)
with that package.

## Source checkout

The source checkout includes unreleased construction-search features. See
[capabilities and limits](../dev/plans/roadmap.md#source-capabilities) before
choosing it for your task.

```bash
git clone https://github.com/e-south/hop-design.git
cd hop-design
uv sync --locked
uv run hop-design --help
```

Use `uv run hop-design` from this checkout for the source examples.

## Continue

- [Compile a first design](quickstart.md).
- [Define and preview a substrate space](substrate-spaces.md).
- [Search junctions and compile a construction](compile-construction.md).
