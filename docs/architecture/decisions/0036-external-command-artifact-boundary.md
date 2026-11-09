# ADR 0036: Expose command and artifact handoffs

Consumers need HOP's exact derivations and rendered material handoffs while
maintaining independent installations. Python model imports unnecessarily
couple their package graphs and API migrations.

Expose named domain commands over existing request, result, and bundle files.
Command adapters call public use cases; they do not derive molecular state.
Machine-readable reports bind exact canonical file contents and expose the
identities and dispositions already computed by HOP. No scientific models,
algorithms, generic RPC dispatch, or executable object representations are
copied into consumers. The current artifact formats and atomic publication
writers remain authoritative.

The HOP installation executing the command reports where it came from separately
from the digest of its actual package contents. Consumers explicitly select its
environment. They may retain a report for later schema and byte checks, but only a producer
execution establishes a fresh deterministic replay claim. Historical frozen
evidence remains unchanged.

The cost is an explicit process invocation and replay when reopening saved records.
The benefit is independent installation and release ownership while retaining
molecular replay checks. CLI parity tests bind report authorities and generated files
to existing public operations; corruption and invalid-input tests preserve
failure behavior. See the [external artifact reference](../../reference/external-artifacts.md).
