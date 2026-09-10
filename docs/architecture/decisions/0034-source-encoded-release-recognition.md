---
doc_id: hop-adr-0034
title: ADR 0034 - Couple source-encoded recognition sites
intent: Distinguish source recognition constraints from later cleavage operations.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-09-08
doc_type: decision
amends:
  - hop-adr-0033
---

# ADR 0034: Couple source-encoded recognition sites

## Decision

A basal future-release requirement identifies the material supplying its
recognition sequence. `source_duplex` is the default; `endpoint_material`
requires explicit selection for a sequence supplied later in the route.

Source-encoded Type IIS and nickase recognition patterns constrain the same
source positions. Their domain intersection determines compatibility before
sequence enumeration. The proximal adapter positions map to source positions
immediately before the payload, directly for the left endpoint and
reverse-complemented for the right endpoint. Cleavage coordinates remain tied
to the characterized enzyme and requested endpoint, not an independent site
placement preference.

An encoded recognition site is not an executed cleavage operation. The local
nicking state applies only its declared enzymes. Type IIS cleavage acts on the
later copied duplex. Intrinsic basal validation replays both the enzyme
definition and its required source-sequence placement.

## Contract and verification

Local requests and basal results use schema version 6. Readers reject other
versions rather than reinterpret their sequence obligations. The material
choice participates in canonical identities; no compatibility reader or alias
is introduced. Source and endpoint-material designs are distinct supported
construction strategies, not interchangeable ways to satisfy one request.

Tests cover source-site presence, compatible and conflicting motif overlap,
payload preservation, separate reaction stages, endpoint-material provision,
and consistently resealed recognition forgeries.
