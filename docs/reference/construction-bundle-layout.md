---
doc_id: hop-construction-bundle-layout
title: Construction bundle layout and verification
intent: Define the portable authority for one payload-centered complete-construction result.
audience:
  - bundle consumers
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-30
doc_type: reference
journey:
  - verify
  - integrate
---

# Construction bundle layout and verification

A construction bundle records one replay-verified complete-construction result
and embeds the separate design bundle on which that result depends. It is not a
method-execution record or experimental evidence package.

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
| `authorities/design/hop-bundle.json` | Manifest for the separately compiled design authority used during construction composition |
| `authorities/design/<artifact>` | Unchanged design artifacts required for complete design semantic replay |

The root manifest inventories every content artifact except itself. No local
projection is embedded in the authority: JSON, CSV, and SVG projection packets
are deterministic views generated from a verified receipt and may be stored
separately.

## Verification

```python
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

The construction bundle has its own identity. It references and embeds a
verified design bundle without redefining that design identity. A construction
result may be `complete`, `infeasible`, or `truncated`; all three are digital
outcomes under declared bounds and a declared molecular model.

The route implementation identity is `complete-construction/7`. It includes
retention of source-derived bases between a basal nick and the payload.
Readers require this identity; results made with another implementation must
be regenerated from their requests. The request and result schemas remain
`hop.construction-request/v6` and `hop.construction-result/v6`.

Verification establishes byte integrity and deterministic molecular replay. It
does not establish that a route was performed, that a product was recovered,
that a destination accepts the product, or that construction, QC, activity,
yield, or empirical enzyme performance succeeded.

See the separate [design bundle](bundle-layout.md) and
[method bundle](method-bundle-layout.md) contracts.
