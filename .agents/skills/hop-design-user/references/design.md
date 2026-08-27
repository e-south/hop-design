# Design language

Use this reference when the requested output is a substrate-space preview,
hairpin design set, checked design, design-space plan, or `HopBundle`.

Read [the language overview](../../../../docs/language/overview.md) and the
matching guide. Use `hop_design` for common operations and types.

For the minimal scientist-facing journey, read the
[substrate-space guide](../../../../docs/guides/substrate-spaces.md) and use
`hop_design.spaces`:

```python
from hop_design.spaces import SubstrateSpaceSpec, compile_space, preview_space

preview = preview_space(spec)
verified = compile_space(spec, destination="build/design-set")
```

Preview writes nothing. Compile accepts only a `ready` space, publishes only a
complete verified package, and refuses an existing destination. The YAML,
CSV, FASTA, and HTML files are projections; `bundle/` is the authority.

```python
import hop_design as hop

compilation = hop.compile(sequence="NRY", design_id="example")
```

- Use `hop.check(spec)` before compiling a caller-authored strict spec.
- Expand symbolic DNA only with `hop.expand_payload` and an explicit budget.
- Calculate design-space cardinality before interpreting rows. Do not drop
combinations or render bundles as a planning side effect.
- A reserve basal profile requires explicit reserve acceptance.
- A successful design compilation establishes a deterministic encoding and its
feature partition. It does not establish a production method.
- A verified design set establishes exhaustive digital member derivation. It
  does not establish physical construction, QC, or biological activity.

For files, name the new output directory, call `Compilation.write()`, then use
the design verifier described in `verification-and-integration.md`.
