# Named methods

Use this reference when exact materials must resolve through an implemented
production method.

Read [the method overview](../../../../docs/methods/overview.md) and import public
operations and contracts from `hop_design.methods`.

- Call `list_method_capabilities()` before constructing a large request when
availability or exactness is uncertain.
- The current linear-source method accepts exact molecular sequences only.
- Compile with `compile_linear_source_multinick_hairpin_pcr(request)`.
- Write a `MethodBundle` only after the result is complete, using
`compile_linear_source_method_bundle(request)`.
- State the transformation-based method ID. Do not substitute a design
derivation identifier.
- Preserve all molecular states, cuts, chemistry, and cohesive-end lineage.

The endpoint is a destination-neutral `RestrictionDigestProduct`. It does not
claim destination compatibility or assembly readiness. Follow
`verification-and-integration.md` after writing a bundle.
