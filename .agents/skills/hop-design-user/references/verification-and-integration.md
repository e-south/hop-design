# Verification and integration

Use this reference after a bundle write or before handing an immutable HOP
product to a consumer.

Read [provenance and verification](../../../../docs/provenance/overview.md).

For a design bundle:

```python
import hop_design as hop

manifest = hop.verify_bundle(path)
verified_design = hop.load_verified_bundle(path)
```

Pass `verified_design.plan.hairpin_encoding_insert`, its sequence digest, and
its nested features without reconstruction.

For a method bundle, use `hop_design.methods.verify_method_bundle(path)` and
`load_verified_method_bundle(path)`. Pass the verified request, plan,
`restriction_digest_product`, cut geometry, and manifest encoding digest.

The consumer compares
`verified_design.plan.hairpin_encoding_insert.sequence_digest` with
`verified_method.bundle.hairpin_encoding_digest` and the product projection
digest. This comparison is caller-owned; it does not merge sibling bundle
identities. Destination placement, assessment, and experimental observations
remain downstream claims.
