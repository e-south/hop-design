---
doc_id: hop-adr-0041
title: Match bounded preparations against an explicit family reference
intent: Recover a controlled comparison without changing requirements or inventing global coverage.
audience: [maintainers, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-04
doc_type: explanation
---

# Reference-bound family matching

Two individually complete preparations can disagree on required scaffold
properties. Admission detects this; it does not find a compatible alternative.
`match_construction_family` adds bounded evaluation against a caller-declared
complete member and zero-based choice. Historical execution and its first-complete
display reference stay unchanged. Matching does not infer a preferred reference.

The input family is captured and replay-admitted before evaluation. The matcher
uses each exact member request and recorded local witnesses. A missing local
search runs under its original domains and quotas. Members are visited by name,
not roster position; recorded foldback/basal pairs are continued in recorded
order under an explicit total bound of 1–64. Per-member local coverage and
unexamined pair counts are retained. Examining all recorded pairs does not imply
exhausting the upstream local domain or searching all jointly compatible families.

The explicit reference is held fixed. Complete candidates are compared with its
required shared properties through the existing verified portrait facts. All
failed and incompatible candidates remain present. No selection, constraint
relaxation, minimum repair or global infeasibility claim is made. An explicit
selected set or family reconciliation performs the existing independent admission
checks before retrieval. A reference without a compatible match can be replaced
only by a new explicit matching request.

`hop.family-matching-result/v1` and `hop.family-matching-packet/v1` describe a
derived, hash-inventoried search packet. It contains the original family, local
receipts, complete outcomes, portraits and selections. Its summary is an index;
the molecular receipts remain authoritative. Publication is create-only and
cannot overlap the captured source. Matching is orchestration; it does not add a
second solver or a study-specific dependency.

`hop.construction-family-preview/v3` adds structured conflict locations and a
dimensioned intent schematic. Both permission and hard-requirement conflicts
are exposed before execution, with explicit edit options. The canonical family
remains the request authority. No search, automatic edit or successful-molecule
claim occurs in preview. Saved molecular records and family outcomes remain
admissible; old preview artifacts stay historical.

The primer-span view draws only the admitted numeric source constraint and its
requested footprint. It cannot stand in for a completed failed molecule. Direct
hairpin reports use recorded endpoint chemistry and a join/contact legend instead
of repeating the same state as a downstream product.

## Maintenance boundaries

| Change | Owning module | Contract to preserve |
| --- | --- | --- |
| Prepared request context | `design/construction/execution/context.py` | Shared request projection, design identity validation and local-selection shape. Family replay does not depend on executor-private context helpers. |
| Recorded local coverage and sole-witness stops | `design/construction/execution/coverage.py` | Execution and family replay derive stops from the same coverage projection. Explicit continuation retains multiple recorded witnesses; coverage never implies global family feasibility. |
| Derived family publication | `design/construction/families/packet.py` | `SourceBoundFamilyPacket` publishes reports, sets, reconciliations and matching packets through the protected create-only exporter. Each operation supplies its captured source roots and schema. |
| Family admission | `design/construction/families/admission.py` and `member_admission.py` | Replay the exact requests and authorities before interpreting saved summaries. |
| Alternative evaluation | `design/construction/families/matching_candidates.py` | Continue recorded witness pairs without changing permissions or selecting a winner. |
| Reader-facing presentation | `export/construction/scaffold/` | Render admitted projection facts; no molecular derivation or study policy. |

`FamilyPacket` also serves source-free request previews and execution captures.
Only packets derived from captured input authorities use `SourceBoundFamilyPacket`.
Both retain their existing schemas and opaque public receipt types. Shared coverage
is an internal presentation projection, not another serialized molecular authority.
