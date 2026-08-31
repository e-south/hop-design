---
doc_id: hop-adr-0031
title: ADR 0031 - Derive exact designs from selected local realizations
intent: Close the route-to-design authority relation without coupling design identity to search execution.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
---

# ADR 0031: Derive exact designs from selected local realizations

## Context

Foldback and basal discovery return replay-verified exact molecular
realizations. Complete construction separately requires a verified design whose
encoding matches one composed route. Requiring callers to author that design
before selecting the local realizations made the payload-first relation
circular and forced arbitrary-length basal geometry through an unrelated
four-position policy contract.

## Decision

`compile_design_from_local_realizations` accepts one exact payload, one selected
foldback realization, and, for a PCR-bearing endpoint, one selected basal
realization. It replays both opaque local receipts, requires exact family,
identity, and payload agreement, and returns the existing `Compilation` result.

The internal `hop.exact-junction-design/v1` specification contains only the
exact payload, foldback junction, basal junction, fixed derivation references,
and caller-owned design id. The corresponding plan derivation is non-temporal
and route-neutral. Local result ids, realization ids, search bounds, relaxation
radii, enzymes, and reaction programs remain construction provenance and do not
enter design authority.

The schema accepts arbitrary equal nonzero basal-arm lengths. It does not reuse
the four-position basal policy model, because that model answers a different
component-assessment question.

Direct single-stranded endpoints are not accepted by this operation until a
caller can supply an exact basal component independently of a PCR-local basal
receipt. No empty basal junction or hidden default is invented.

## Consequences

Two molecularly identical selections found under different search bounds
produce byte-identical specifications, plans, and bundles when the caller-owned
design id is the same. Two distinct exact junction selections produce distinct
design authorities. Either authority can be written, replay-verified, and
passed unchanged to complete construction.

The operation does not select a preferred realization, assert that a search was
complete, or claim physical construction, folding, cleavage, ligation,
recovery, quality control, or activity.
