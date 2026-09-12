---
doc_id: hop-quickstart
title: Compile a first HOP design
intent: Compile a public duplex substrate and preview a realistic variable-spacer family.
audience:
  - new users
owner: HOP Design maintainers
status: active
last_verified: 2026-09-10
doc_type: tutorial
journey:
  - compile
  - verify
---

# Quickstart

[Install HOP](install.md), then compile one exact payload. The installation
guide distinguishes the released package from the source checkout. Commands
beginning with `uv run` below assume you are in that checkout.

## Compile an exact payload

From a source checkout, prefix this command with `uv run`.

```bash
hop-design compile --sequence ATAACTTCGTATAGCATACATTATACGAAGTTAT \
  --design-id loxp-payload --out build/loxp-exact
```

The command prints the design and saved-file identifiers. Open the output
directory to inspect the sequence and feature files.

The payload is a public 34-bp loxP reference. HOP preserves it and derives the
paired arm; it does not model Cre activity. The
[worked junction example](../../examples/basal-junction/README.md#source-definitions)
records the sequence source.

## Preview a sequence space

The eight-base spacer between loxP's fixed recognition arms defines a meaningful
variable region. From a source checkout, preview all spacer sequences:

```bash
uv sync --locked
uv run hop-design space preview examples/loxp-spacer.yaml
```

This defines 65,536 paired payloads, not independently randomized arms.
Preview writes nothing and reports that exhaustive compilation exceeds the
current 256-member limit. The family can still be represented symbolically;
one exact member does not establish construction compatibility for the pool.
The [substrate-space guide](substrate-spaces.md) explains the input grammar.

## Specify one design

```bash
uv run hop-design compile --sequence ATAACTTCGTATANNNNNNNNTATACGAAGTTAT \
  --design-id loxp-spacer-family --out build/loxp-symbolic
```

The CLI refuses to replace an existing output directory. Add `--dry-run` to derive the
design and check its constraints without writing; `--out` is not required for
that read-only call.

A strict JSON or YAML specification can be supplied with `--spec FILE`.
Use `hop.design/v2` for the standard hairpin context and `hop.resolved-design/v2`
when supplying foldback and basal components. The
[design language](../language/overview.md) describes these specialist inputs.

In Python:

```python
import hop_design as hop

spec = hop.create_spec(
    sequence="ATAACTTCGTATANNNNNNNNTATACGAAGTTAT", design_id="loxp-spacer-family"
)
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
- [Search a basal junction with characterized enzymes](../../examples/basal-junction/README.md) or
  [compile a construction](compile-construction.md) through Python.
- [Check a named method](resolve-production-method.md) and
  [render molecular views](render-component-views.md).

The CLI can also inspect and select saved constructions with
`hop-design construction`. Construction search and compilation use Python;
check the [construction guide](compile-construction.md) for source-only features
not available in the published release.
