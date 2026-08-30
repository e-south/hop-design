---
doc_id: hop-provenance-verification-overview
title: Provenance and verification
intent: Explain bundle identity, semantic replay, digests, and cross-product handoffs.
audience:
  - users
  - integrators
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: explanation
journey:
  - verify
  - integrate
---

# Provenance and verification

HOP uses “provenance and verification” for derivation claims. Experimental
observations and biological interpretation remain outside HOP.

## Three bundle authorities

```text
DesignSpec -> DesignDerivation -> HairpinEncodingInsert -> HopBundle

ConstructionSource + verified HopBundle
  -> local authorities -> complete route result -> ConstructionBundle

MethodRequest -> molecular states -> RestrictionDigestProduct -> MethodBundle
```

Each bundle has its own identity and replay claim. The construction bundle
embeds the complete verified design bundle used during composition; it does not
reconstruct or rename that design authority. The method bundle remains a
sibling authority for one named method request and does not become construction
evidence merely because an encoding digest agrees.

## The construction handoff

```python
import hop_design.construction as construction

compiled = construction.compile_construction(
    "construction.yaml",
    design_bundle_path="design",
)
bundle_path = compiled.write("construction")
verified = construction.load_verified_construction_bundle(bundle_path)
```

The loader checks the root inventory and digests, replays the embedded design,
replays each local authority, recomposes the complete route, and requires the
expected result, artifacts, and root manifest to match. Opaque public receipts
expose identity and accounting without making raw replay models public.

## The design-method handoff

A method product can project the one-dimensional hairpin encoding that it
physically realizes. Run the matched public example from a contributor
checkout:

```bash
uv run python examples/verify_design_method_handoff.py \
  --out build/matched-handoff
```

The example compiles the [matched design fixture](../../examples/linear-source-matched-design.yaml)
and the existing public method request, writes each sibling bundle independently,
and reloads each through its semantic verifier. The consuming application then
checks exact digest equality:

```python
import hop_design as hop
import hop_design.methods as methods

verified_design = hop.load_verified_bundle("build/matched-handoff/design")
verified_method = methods.load_verified_method_bundle("build/matched-handoff/method")

design_digest = verified_design.plan.hairpin_encoding_insert.sequence_digest
method_digest = verified_method.bundle.hairpin_encoding_digest
projection_digest = (
    verified_method.plan.restriction_digest_product.hairpin_encoding_projection.sequence_digest
)
assert design_digest == method_digest == projection_digest
```

The command prints both verification statuses, both bundle identifiers, and the
three equal digests as JSON. The fixtures are a synthetic contract demonstration,
not a protocol or biological recommendation. The loaders replay each bundle
independently. They do not infer a relationship between sibling bundles; the
consumer owns and records this equality check.

## What verification establishes

- every manifest entry matches its bytes;
- strict schemas reject unknown or retired fields;
- derived artifacts replay from their authoritative inputs;
- feature partitions, spans, sequences, and digests agree;
- method states preserve cut, fragment, bond, and per-base lineage;
- construction results preserve local authority membership, reaction
  assessment, examined composition dispositions, exact endpoint products,
  rejection reasons, and reversible grouping;
- each bundle is internally replayable and digest-consistent.

Verification does not establish destination compatibility, protocol yield, or
experimental success.

See [plans, artifacts, and bundles](plans-artifacts-and-bundles.md), the
[design-bundle layout](../reference/bundle-layout.md), and the
[construction-bundle](../reference/construction-bundle-layout.md) and
[method-bundle](../reference/method-bundle-layout.md) layouts.
