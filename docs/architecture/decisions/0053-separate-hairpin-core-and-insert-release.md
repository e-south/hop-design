---
doc_id: hop-adr-0053
title: Separate hairpin-core geometry from insert-release boundaries
intent: Preserve basal association while deriving exact retained insert strands independently.
audience: [maintainers, integrators]
owner: HOP Design maintainers
status: accepted
last_verified: 2026-10-09
doc_type: decision
---

# Separate hairpin-core geometry from insert-release boundaries

The design compiler describes paired basal arms around the supplied stem and
foldback. Complete construction previously required the final Type IIS cut union
to equal that design sequence. This conflated source–adapter association with
later insert retention. It rejected unequal end-to-stem distances even when exact
primer tails, source ancestry and cuts supported them. Trimming both design arms
to one release requirement also erased association positions from the core.

## Decision

Keep the route-neutral paired design core intact. Derive its occurrence in the
PCR parent from the source embedding and forward-primer extension; do not locate
it by searching for a matching word. Repeated sequence cannot transfer the
supplied-stem annotation to another occurrence.

Released-insert products carry `ReleasedInsertEvidence`: the exact parent state
and strand identities, the parent-core projection, the released union projection,
and the retained span on each parent strand. The core and union use the parent
reference-strand coordinates; each retained strand span uses that strand's own
5-prime-to-3-prime coordinates. Replay derives these facts independently.

Four actual cuts determine retention. Both strands must retain the entire
interval from the first supplied-stem boundary through the paired supplied-stem
boundary, including the foldback. The cuts may retain construction DNA outside
the core or remove its outer construction bases. Requested sticky words,
polarities and paired gaps must still match exactly. No new reaction or relaxed
sequence-preservation rule is introduced.

PCR fate records use the same per-strand retention boundaries. Primer-derived
bases can be retained construction; outer core bases can be transient. Material
function and final fate remain separate facts.

Unreleased endpoints keep their endpoint `encoding_projection`. Released inserts
require only `release_evidence`; mixed, missing and retired clone projection forms
fail closed. `design_projection` is a read-only accessor to the appropriate core
projection, whose coordinate frame remains explicit in the serialized authority.

## Consequences and checks

Construction-space-result v9 and complete-construction implementation 11 bind the
new evidence. Old bundles require their recorded producer or regeneration from
authored inputs. There is no schema relabeling or compatibility alias.

Regression cases cover unequal 6/0-bp gaps through added primer-tail sequence,
2/0-bp gaps through removal of outer construction bases, unchanged basal contact
records, source-anchored repeated sequences, per-strand fates, and tampering with
each release fact. A cut into either supplied-stem boundary on only one strand is
rejected even if the union still contains the complete protected interval.
Direct-hairpin and PCR-only molecular golden records remain byte-identical;
their versioned result envelopes change.

This removes a representation restriction. It does not establish that every
requested interface has a complete route, that an arbitrary primer tail is
permitted, or that a modeled preparation has been recovered experimentally.
