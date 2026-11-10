# Provenance and verification

HOP saves each bundle's inputs, derived results and content-based identifiers.
Verification reruns the derivation and compares the result with the saved files;
this is **replay**. A **digest** is a fingerprint calculated from content, used
to detect changes or compare exact sequences. Callers retain observations and
biological interpretation in their own records.

## Three bundle authorities

```text
DesignSpec -> DesignDerivation -> HairpinEncodingInsert -> HopBundle

ConstructionSource + verified HopBundle
  -> local authorities -> complete route result -> ConstructionBundle

MethodRequest -> molecular states -> RestrictionDigestProduct -> MethodBundle
```

Each bundle has its own identifier and derivation to verify. It is the
**authority** for the result it records. The construction bundle embeds the
complete verified design bundle used during composition, preserving that
design's identity and files. The method bundle independently records one named
method request. Matching an encoding digest links the sequence described by the
two bundles; it does not supply the complete-construction checks.

## The construction handoff

```python
# Compile and re-admit the construction bundle before using its results.
import hop_design.construction as construction

compiled = construction.compile_construction(
    "construction.yaml",
    design_bundle_path="design",
)
bundle_path = compiled.write("construction")
verified = construction.load_verified_construction_bundle(bundle_path)
```

The loader checks the file inventory and digests, replays the embedded design
and each local result, recomposes the complete route, and requires the expected
result, output files and root manifest to match. It returns a verified receipt:
an API object that exposes identifiers and result counts while keeping the
internal replay models private.

## The design-method handoff

A method product can report the one-dimensional hairpin encoding contained in
its modeled strands. Run the matched public example from a contributor
checkout:

```bash
# Write the independent design and method bundles for this synthetic example.
uv run python examples/verify_design_method_handoff.py \
  --out build/matched-handoff
```

The example compiles the [matched design fixture](../../examples/linear-source-matched-design.yaml)
and the existing public method request, writes each sibling bundle independently,
and reloads each through its semantic verifier, which reruns its derivation.
The consuming application then checks exact digest equality:

```python
# Verify both bundles before comparing their sequence digests.
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
three equal digests as JSON. The fixtures use synthetic inputs. The loaders
replay each bundle independently; the consumer records the digest equality that
links them.

## What verification establishes

- every manifest entry matches its bytes;
- strict schemas reject unknown or retired fields;
- derived output files are reproduced from their recorded inputs;
- feature partitions, spans, sequences, and digests agree;
- method states preserve cut, fragment, bond, and per-base lineage;
- construction results preserve local authority membership, reaction
  assessment, examined composition dispositions, exact endpoint products,
  rejection reasons, and reversible grouping;
- each bundle is internally replayable and digest-consistent.

See [plans, artifacts, and bundles](plans-artifacts-and-bundles.md), the
[design-bundle layout](../reference/bundle-layout.md), and the
[construction-bundle](../reference/construction-bundle-layout.md) and
[method-bundle](../reference/method-bundle-layout.md) layouts.
