---
doc_id: hop-why-hop
title: Why HOP
intent: Explain the value and limits of searching construction sequence around an unchanged duplex payload.
audience:
  - users
  - integrators
owner: HOP Design maintainers
status: active
last_verified: 2026-09-08
doc_type: explanation
journey:
  - compile
  - integrate
---

# Why HOP

The region being tested should not have to change to accommodate its
construction sequence. For a unimolecular DNA hairpin, that means preserving
the duplex payload while arranging the flanking recognition sites, exposed
strands, pairing regions, and joining bonds needed to assemble it.

HOP makes those arrangements searchable. You can ask which enzymes permit a
requested foldback, how close a basal nick can lie to the payload, or which
cuts remove unwanted source fragments. Results retain exact molecular examples
and the bounds under which they were found, so a junction can be inspected
rather than inferred from a final sequence string.

Local junctions are only part of the problem. A proposed construction also
needs sufficient adapter pairing, primer-binding sequence, and compatible
processing steps. Checking these together can expose a missing requirement
even when both local junctions are feasible.

The useful output is an inspectable sequence and material specification for
testing, not a prediction of experimental success. HOP models established
copying, cleavage, association, and joining operations; it does not predict
their efficiency or establish library-wide physical recovery from one example.

Start with [the molecular steps](mental-model.md), then
[search a construction](../guides/compile-construction.md) or
[define a substrate space](../guides/substrate-spaces.md).
