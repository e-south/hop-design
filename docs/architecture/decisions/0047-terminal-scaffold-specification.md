---
doc_id: hop-adr-0047
title: Terminal scaffold specification
intent: Translate explicit terminal requirements while retaining molecular authority and permissions.
audience: [maintainers, integrators]
owner: HOP Design maintainers
status: active
last_verified: 2026-10-06
doc_type: explanation
---

# Terminal scaffold specification

An experimentalist can request the terminal form of a complete hairpin without
authoring adapter annealing coordinates. `hop.scaffold-discovery/v2` introduces
this translation. Version 1 discovery retains its existing interpretation and
rejects terminal declarations. Achieved-state scaffold checks accept inclusive
unpaired 5-prime and 3-prime nucleotide counts, separate from terminal chemistry.

`models.construction.hairpin_geometry.HairpinArchitecture` owns terminal counts
as properties of its verified spans and continuous strand. Admission, comparison
and export consume these same facts. Existing portrait serialization retains its
sealed spans; no redundant mutable terminal-count authority is added. The supported
architecture remains one contiguous paired region, one loop and a forward stem.

With explicit adapter redesign permission, `design.construction.discovery.terminals`
proposes finite pairing settings for the adapter-ligated hairpin endpoint. Basal
placement uses the existing kernel, including enzyme-dependent source offsets.
Fixed-source stem occurrences are candidate locations only; complete embedding,
source/primer policies and achieved terminal checks remain authoritative.
Preview limits source lengths, candidate positions and placements to 256 each;
the existing 256-branch expansion ceiling and execution quotas remain in force.

Three-prime tail choices are either prefixes of the existing declared handle or
an explicitly supplied finite list of exact sequences. Redesign permission
authorizes those edits; length alone never creates bases. Empty tails use the
existing derived-adapter policy. Fixed adapters cannot be rewritten. Required
open-side pairing and terminal counts must hold together. A candidate setting
does not prove reaction feasibility, recovery or assembly compatibility.

The [public workflow](../../guides/discover-product-scaffolds.md) retains explicit
selection and portable preparation retrieval. Terminal comparison sheets consume
verified whole-molecule portraits and material identities, retain molecular stage
and polarity, and state when a long terminal sequence is cropped.

The [delivery plan](../../dev/plans/terminal-scaffold-comparisons.md) also tracks
stage-qualified controls, required-member search and reference-material reuse as
separate increments. This terminal contract does not imply those deliveries are
already complete.
