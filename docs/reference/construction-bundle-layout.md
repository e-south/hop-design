# Construction bundle layout and verification

A construction bundle records one replay-verified complete-construction result
and embeds the separate design bundle on which that result depends.

```text
construction-bundle/
├── construction-bundle.json
├── construction-result.json
└── authorities/
    └── design/
        ├── hop-bundle.json
        └── <every artifact inventoried by that design bundle>
```

| Path | Meaning |
| --- | --- |
| `construction-bundle.json` | Content-addressed root manifest with the construction result identity, embedded design-bundle identity, root digests, and complete artifact inventory |
| `construction-result.json` | Exact local authorities, examined composition prefix, accepted route realizations, endpoint products, rejection accounting, grouping, provenance, and claim boundary |
| `authorities/design/hop-bundle.json` | Manifest for the separately compiled design bundle used during construction composition |
| `authorities/design/<artifact>` | Unchanged design artifacts required for complete design semantic replay |

The root manifest inventories every content artifact except itself. JSON, CSV,
and SVG projection packets are generated from a verified receipt and stored
separately from the bundle.

## Verification

```python
# Admit the saved construction through its semantic verifier.
import hop_design.construction as construction

verified = construction.load_verified_construction_bundle("construction-bundle")
```

Loading rejects missing, modified, symlinked, unsafe, or unmanifested content.
It then:

1. validates the strict root manifest and complete artifact inventory;
2. checks the result digest, manifest digest, bundle identity, and embedded
   design-bundle identity;
3. semantically replays the complete embedded design bundle;
4. parses the construction result and replay-verifies its foldback and optional
   basal local authorities;
5. recomposes the complete route against those verified authorities and the
   verified design; and
6. recompiles the expected construction bundle and requires exact artifact and
   manifest equality.

Updating checksums after changing a result, local authority, design artifact,
reaction metric, rejection reason, route product, or grouping therefore does
not satisfy verification.

The returned `VerifiedConstructionBundle` is an opaque read-only receipt. It
exposes bundle, result, and design identities; endpoint and status; exact
realization counts; examined and nominal combination counts; and accepted
materialized-realization identities. Raw result and manifest models are not
part of the public facade.

## Identity and claim boundary

The construction bundle has its own identity and preserves the embedded design
bundle's identity. Its result records `complete`, `infeasible`, or `truncated`
under the declared bounds and molecular model.

The route implementation identity is `complete-construction/11`. It includes
retention of source-derived bases between a basal nick and the payload and
composition of selected cleanup nicks into PCR-bearing routes. Each such route
embeds its selected partition request and realization as `source_partition_plan`,
so individual-route validation can replay cuts, fragment lineage, and selection.
The field is omitted when no cleanup plan is consumed.
Current readers require this identity; regenerate results made with another
implementation from their preserved requests. The request and result schemas
are `hop.construction-discovery-request/v7` and `hop.construction-space-result/v9`;
the bundle schema is `hop.construction-bundle/v6`.

Verification checks byte integrity and replays the molecular derivation.

See the separate [design bundle](bundle-layout.md) and
[method bundle](method-bundle-layout.md) contracts.
