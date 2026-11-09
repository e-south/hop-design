# Plans, artifacts, and bundles

HOP keeps sequence anatomy, complete constructions and named methods in separate
bundles. A **plan** records derived structure or processing states. An **artifact**
is an output file, such as FASTA or SVG. A **bundle** stores the inputs, plan and
artifacts with a manifest listing their paths and content digests. Use the
verified loaders below to check them.

## Design compilation

```text
HopSpec or ResolvedHopSpec
    -> DesignDerivation
    -> HopPlan
    -> HairpinEncodingInsert
    -> HopBundle
```

The spec is authored intent. `HopPlan` is the immutable compiler result. It
derives the paired payload, evaluates selected components, partitions the
normalized encoding into typed features, and records how those design values
were derived. Its `design_derivation` does not describe processing order. A
resolved design may preserve caller-asserted nick or release projection geometry;
construction
programs and method plans record the ordered processing steps.

Every design bundle contains:

```text
hop-bundle.json
hop-plan.json
hop-spec.json
provenance.json
hairpin-encoding.fasta
```

Explicit component designs also contain deterministic JSON and SVG review views.

## Complete construction

A construction combines a verified design with selected local junctions, source
preparation and required materials. Its `ConstructionProgram` records ordered
molecular states and transitions through the requested endpoint. The
`ConstructionBundle` embeds the design bundle it used, the complete route and
material specifications. See the [construction-bundle layout](../reference/construction-bundle-layout.md).

## Method resolution

```text
MethodRequest
    -> exact molecular states and transitions
    -> MethodPlan
    -> destination-neutral product
    -> MethodBundle
```

A `MethodPlan` records the ordered states of one named method. Its bundle records
the exact request, complete plan, trajectory, modeled molecular
products, and derived exports.

## Verification

Bundle identifiers derive from manifest content. Verification checks paths and
inventory, validates every digest, reloads strict schemas, and reruns the
compiler from the recorded inputs. This is replay. Recalculating the digests
after changing an output file cannot make it valid: replay must reproduce every
stored byte.

Use `load_verified_bundle()` for a design,
`load_verified_construction_bundle()` for a complete construction, and
`load_verified_method_bundle()` for a named method. Retain the verified object
and its digests when passing results between these operations.

## Cross-bundle relation

Design and method bundles do not share identity. When a method claims to
realize a design, the consumer checks equality of the design encoding digest
and the method product's encoding-projection digest. See
[provenance and verification](overview.md).
