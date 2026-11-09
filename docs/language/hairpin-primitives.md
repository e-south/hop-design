# Hairpin components

Use these components to describe a hairpin's sequence anatomy and paired regions.
Construction programs describe how those components are made and processed.

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

The payload is the caller-authored input sequence. It may be exact DNA or use DNA
IUPAC symbols to permit several bases at a position. HOP derives the paired
payload by reverse complement; the paired payload is not a second independently
authored payload.

### Foldback junction

A foldback junction contains:

- a retained tract at the closed end;
- the unpaired turn connecting the two arms;
- a returning foldback arm; and
- a record of how each aligned pair of bases in the retained tract and
  returning arm interacts.

The **foldback stem** is that pairing relationship, not another sequence block.
Turn length and paired-tract length are therefore the independent geometric
controls. HOP also measures uninterrupted paired runs and records the exact
bases at noncanonical pairs, such as G:T wobbles or mismatches.

“Cap” is informal. Specify whether it means the unpaired loop or also includes
nearby paired bases, then map it to the foldback junction's exact spans. A
turn-only topology has no retained tract, no foldback arm, and no pair calls.

A recognition motif that enables nicking or cleavage is part of precursor and
method geometry. It does not become a second definition of the cap.

### Basal junction and stem extension

The basal junction is the paired open end of the hairpin. The specialist
four-position basal-pairing evaluation classifies S3 through S0 as Watson-Crick,
G:T wobble, or hard mismatch. Its compact M/W/X string reports those contacts.
Complete-construction basal association records the source–adapter contact region
separately and can span more positions; see the
[construction vocabulary](ontology/molecular-meaning-and-search.md#payload-centered-construction-vocabulary).

In the specialist design anatomy, longer non-payload paired context belongs to
`PairedStemExtension`. It is separate from the four-position basal profile.
Nicked and surviving strand roles belong to processing events, not to the
basal junction itself.

## Products and handoffs

`HairpinEncodingInsert` contains HOP's compiled sequence and the named regions
within it. It represents sequence order on one axis. Strands and assembly ends
belong to the product records below.

`HairpinPcrDuplex` is the exact two-strand product modeled by a named method.
`RestrictionDigestProduct` is a destination-neutral duplex fragment made from
that product. A caller creates an `AssemblyFragment` only after choosing a
destination, orientation, and compatible ends.

See the [method language](../methods/overview.md) for event order and the
[formal ontology](ontology.md) for exact contract names.
