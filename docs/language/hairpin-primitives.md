---
doc_id: hop-hairpin-components
title: Hairpin components
intent: Explain the sequence regions and modeled molecular products owned by HOP.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-08-23
doc_type: explanation
journey:
  - compile
---

# Hairpin components

HOP uses sequence regions with one physical meaning each. Historical labels can
map to these regions, but they do not redefine them.

## Design anatomy

```text
basal-left ─ optional stem extension ─ payload
                                             \
                              retained tract ─ turn ─ foldback arm
                                             /
basal-right ─ optional stem extension ─ paired payload
```

The diagram is an ordering aid, not a drawing of strand topology.

### Payload and paired payload

The payload is the caller-authored input sequence. It may be exact DNA or a DNA
IUPAC domain. HOP derives the paired payload by reverse complement; the paired
payload is not a second independently authored payload.

### Foldback junction

A foldback junction contains:

- a retained tract at the closed end;
- the unpaired turn connecting the two arms;
- a returning foldback arm; and
- the aligned pair observations between the retained tract and returning arm.

The **foldback stem** is that pairing relationship, not another sequence block.
Turn length and paired-tract length are therefore the independent geometric
controls. HOP also records uninterrupted paired-run measurements and literal
noncanonical pairs.

“Cap” is descriptive or historical language, not one canonical HOP component.
Depending on its source, a historical cap label may cover the turn, a complete
foldback junction, or another inherited interval. A caller must map it to exact
HOP spans. A turn-only topology has no retained tract, no foldback arm, and no
invented pair calls.

A recognition motif that enables nicking or cleavage is part of precursor and
method geometry. It does not become a second definition of the cap.

### Basal junction and stem extension

The basal junction is the paired open end of the hairpin. HOP's current basal
evaluation classifies four ordered positions, S3 through S0, as Watson-Crick,
G:T wobble, or hard mismatch. The compact M/W/X string reports those physical
calls; it is not an enzyme route or a ligation score.

Longer non-payload stem context belongs to `PairedStemExtension`. This keeps a
variable-length stem from silently enlarging the four-position basal profile.
Nicked and surviving strand roles belong to processing events, not to the
basal junction itself.

## Products and handoffs

`HairpinEncodingInsert` is HOP's one-dimensional compiled sequence and nested
feature map. Despite the word “insert,” it does not claim a physical duplex or
destination readiness.

`HairpinPcrDuplex` is the exact two-strand product modeled by a named method.
`RestrictionDigestProduct` is a destination-neutral duplex fragment made from
that product. A caller creates an `AssemblyFragment` only after choosing a
destination, orientation, and compatible ends.

These records are digital molecular authorities. Verification replays their
derivation but does not establish that a molecule was constructed or recovered.

See the [method language](../methods/overview.md) for event order and the
[formal ontology](ontology.md) for exact contract names.
