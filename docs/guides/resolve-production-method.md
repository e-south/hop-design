---
doc_id: hop-guide-resolve-production-method
title: Resolve and verify a production method
intent: Compile the public linear-source request into a verified MethodBundle and inspect its destination-neutral product.
audience:
  - Python users
  - integrators
  - agent executors
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: how-to
journey:
  - method
  - verify
  - integrate
---

# Resolve and verify a production method

The linear-source method requires exact materials. It resolves every named
molecular state and produces a destination-neutral `RestrictionDigestProduct`.
It does not establish compatibility with a vector or other destination.

## Author every input explicitly

Use the readable authoring example when constructing a request for the first
time:

```bash
uv run python examples/author_linear_source_method.py \
  --out build/authored-linear-source-method
```

The script constructs all six oligos, their terminal modifications, both
nicking agents, the fragment-length rule, adapter-pairing limits, the Type IIS
agent, and the expected encoding before compiling. It writes and reloads a
`MethodBundle`; no private catalog, hidden material, or method default fills a
missing field.

## Replay the canonical JSON fixture

Use the compact JSON fixture when testing serialization and replay:

```bash
uv run python examples/compile_linear_source_method.py \
  --out build/linear-source-method
```

The example performs the complete public path:

```python
import hop_design.methods as methods

request = methods.LinearSourceMultinickHairpinPcrRequest.model_validate_json(
    request_path.read_text(encoding="utf-8")
)
compilation = methods.compile_linear_source_method_bundle(request)
compilation.write(output_path)
verified = methods.load_verified_method_bundle(output_path)
product = verified.plan.restriction_digest_product
```

Compilation fails closed when the exact request is infeasible. Writing refuses
to replace an existing directory. Loading verifies the manifest, request,
method plan, molecular states, exports, and semantic replay before returning a
typed object.

The product carries exact strands, restriction sites, cut geometry, cohesive
ends, per-base lineage, and an encoding projection. A consumer may compare
`verified.bundle.hairpin_encoding_digest` with a separately verified design
bundle, as described in [provenance and verification](../provenance/overview.md).
Destination compatibility remains downstream.

To run that caller-owned equality check with an intentionally matched public
design, use `uv run python examples/verify_design_method_handoff.py --out
build/matched-handoff` from a contributor checkout. The example writes and
verifies separate design and method bundles before comparing their encoding
digests.

See the [method overview](../methods/overview.md), [material contract](../reference/linear-source-method-materials.md),
and [method-bundle layout](../reference/method-bundle-layout.md).
