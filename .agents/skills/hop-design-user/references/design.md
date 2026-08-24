# Design language

Use this reference when the requested output is a checked design, a compiled
design, a design-space plan, or a `HopBundle`.

Read [the language overview](../../../../docs/language/overview.md) and the
matching guide. Use `hop_design` for common operations and types.

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

For files, name the new output directory, call `Compilation.write()`, then use
the design verifier described in `verification-and-integration.md`.
