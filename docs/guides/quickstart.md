---
doc_id: hop-quickstart
title: HOP Design quickstart
intent: Compile and verify one exact and one symbolic demonstration design.
audience:
  - new users
owner: HOP Design maintainers
status: active
last_verified: 2026-08-29
doc_type: tutorial
journey:
  - install
  - compile
  - verify
---

# Quickstart

This page distinguishes the unreleased v0.1.0a8 source candidate from the
published v0.1.0a7 wheel. Use the release's
[tagged documentation](https://github.com/e-south/hop-design/tree/v0.1.0a7)
when operating the published artifact.

Download a versioned wheel and `SHA256SUMS` from
[GitHub Releases](https://github.com/e-south/hop-design/releases), verify the
wheel's checksum, and install it into a Python 3.12–3.14 environment. HOP is not
published on PyPI.

```bash
# macOS
grep 'hop_design-0.1.0a7-py3-none-any.whl$' SHA256SUMS | shasum -a 256 -c -
# Linux
grep 'hop_design-0.1.0a7-py3-none-any.whl$' SHA256SUMS | sha256sum -c -
uv venv --python 3.12
source .venv/bin/activate
uv pip install ./hop_design-0.1.0a7-py3-none-any.whl
hop-design compile --sequence ACGT --design-id exact-demo --out build/exact
```

The release-wheel command above uses the a7 contract. The published a7 wheel supports the
single-design command above and the
scientist-facing substrate-space journey below.

From a contributor checkout:

```bash
uv sync --locked
uv run hop-design space preview examples/fixed-site-three-base-context.yaml
uv run hop-design space compile examples/fixed-site-three-base-context.yaml \
  --out build/fixed-site-three-base-context
uv run hop-design verify build/fixed-site-three-base-context/bundle
```

The example defines 64 exact designs from three variable paired positions.
Open `build/fixed-site-three-base-context/review.html` to inspect the substrate
anatomy, complete space accounting, evidence boundary, exact sequence table,
and handoff files. The package establishes verified digital design; it does
not evaluate a named method or destination, and it does not record physical
construction, QC, or biological activity. Continue with the
[substrate-space guide](substrate-spaces.md) for the specification and package
contracts.

`hop_design.spaces` is the scientist-facing Python facade for this journey.
The package root `hop_design` and the `hop_design.discovery`,
`hop_design.methods`, and `hop_design.views` facades expose specialist design,
bounded-search, named-method, and typed-projection questions; they are not
required to compile the 64-member verification fixture.

The existing single-design route remains available:

```bash
uv run hop-design compile --sequence ACGT --design-id exact-demo --out build/exact
uv run hop-design compile --sequence NRY --design-id symbolic-demo --out build/symbolic
```

The single-design CLI prints the named default, plan ID, and bundle ID. It
refuses to replace an existing output directory. Add `--dry-run` to derive the
design and check its constraints without writing; `--out` is not required for
that read-only call.

A strict JSON or YAML specification uses the same endpoint:

```bash
uv run hop-design compile --spec examples/generic-symbolic.yaml --out build/from-spec
```

The release-wheel and contributor-checkout commands use the same a7 contract.
Use `hop.design/v2` for the named generic demonstration and
`hop.resolved-design/v2` when foldback and basal components are supplied by the
caller. A design spec records deterministic design derivation, not an ordered
construction or laboratory chronology. A resolved release projection requires
explicit terminal-nick geometry; construction routes and named methods own
their respective ordered molecular histories.

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

The generic design derivation builds `basal left + payload + foldback junction + derived
paired payload + basal right`. It exists to exercise the software contracts and
must not be interpreted as a wet-lab protocol or experimental validation.

The CLI intentionally exposes the common compile path. Continue in Python with:

- [payload records and advanced composable axes](payload-sources-and-expansion.md);
- [a bounded basal-candidate query](discover-compatible-basal-candidates.md);
- [a named processing-method bundle](resolve-production-method.md); or
- [route-neutral foldback and basal views](render-component-views.md); or
- [verified consumer integration](../provenance/overview.md).
