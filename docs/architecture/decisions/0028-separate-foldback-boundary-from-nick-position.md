---
doc_id: hop-adr-0028
title: ADR 0028 - Separate the foldback boundary from the nick position
intent: Represent foldback closure routes whose nick lies inside the first retained arm without moving the biological payload boundary.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-30
doc_type: decision
amends:
  - hop-adr-0025
  - hop-adr-0027
---

# ADR 0028: Separate the foldback boundary from the nick position

## Context

The foldback begins at the final payload boundary, but a valid construction
route may nick the source strand inside the first retained foldback arm. The
v1 foldback target used `junction_offset_nt` for both facts. That representation
could describe only routes in which the nick and final foldback boundary were
coincident, or it could move the claimed foldback boundary away from the
payload to compensate.

These interpretations are not equivalent. Moving the foldback boundary changes
the retained molecular object, while moving the nick changes which source
strand contributes each retained base.

## Decision

The active foldback target contains:

- `nick_offset_within_foldback_nt`;
- `loop_length_nt`; and
- `annealing_arm_length_bp`.

The offset is measured from the fixed payload/foldback boundary into the first
annealing arm and must not exceed that arm's length. Let payload length be
\(P\), arm length be \(A\), loop length be \(L\), and nick offset be \(o\).
The source coordinates are derived as:

\[
\text{nick}=P+o
\]

\[
\text{source terminus}=P+2A+L-o
\]

After cleavage and denaturation, the retained reference fragment contributes
the payload and the first \(o\) foldback bases. The complementary fragment
contributes the remaining foldback bases and the paired payload arm. Literal
foldback pairs therefore retain their exact pre-ligation fragment identities;
one pair may span two fragments.

The public construction contract moves to v2 as one coordinated cutover. HOP
does not reinterpret v1 authorities, accept the retired field, or provide an
alias. Design and named-method authorities remain unchanged.

## Consequences

Foldback discovery can recover internal-nick geometries while preserving one
biological payload boundary. Source length, released fragments, lineage,
ligation, retained construction count, projection rows, and all construction
identities derive from the explicit offset.

The change does not make auxiliary cleanup nicks part of the foldback target.
Multi-site source partitioning and endpoint materialization remain separate
route-level questions that complete construction must compose and reassess on
exact molecular states.
