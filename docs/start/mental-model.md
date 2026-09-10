---
doc_id: hop-mental-model
title: From payload to hairpin construction
intent: Explain the fixed payload, searchable junctions, required materials, and limits of a computed construction.
audience:
  - users
  - integrators
  - maintainers
owner: HOP Design maintainers
status: active
last_verified: 2026-09-10
doc_type: explanation
journey:
  - compile
  - discover
  - method
  - verify
  - integrate
---

# From payload to hairpin construction

Start with the duplex sequence you want the hairpin to present. That payload
stays fixed while HOP searches the surrounding sequence and enzyme arrangements.
You can inspect where a junction is possible, what bases and cuts it requires,
and whether selected junctions can be completed into the requested product.

## What do you specify?

Author one payload arm as exact DNA or fixed and degenerate positions. HOP
derives its complementary arm; you do not specify the two independently.
Compiling this anatomy gives the intended hairpin sequence, not a construction
procedure. See [substrate spaces](../guides/substrate-spaces.md).

For construction, also specify the endpoint, available enzymes, local geometry,
pairing requirements, and finite search limits. The physical starting material
is a source ssDNA oligo with construction flanks around the payload. Its sequence
and required auxiliaries depend on the chosen route.

## What can the search change?

The foldback neighborhood supplies the sequence that can be exposed, folded,
and joined to close the cap. The basal neighborhood supplies the opposite
junction, including adapter pairing and later end generation when required.
Neither search changes the payload.

Foldback-local discovery treats the PCR-amplified material as a duplex. Unless
the caller constrains the physical nick strand, HOP searches both exact nick
strands by default and retains only routes permitted by the enzyme's declared
recognition orientation and cut contract.

For a basal search, the cohesive end can be fixed or specified as an IUPAC
pattern. Pairing constraints determine where an adapter may differ from the
displaced source strand. Recognition sites must be valid in the molecular state
where the relevant enzyme acts; a later adapter cannot supply a site required
in the initial source duplex.

Searches explore increasing retained non-payload sequence. An existence search
keeps a witness for each accessible work unit; an all-realizations search keeps
every exact alternative within its reported coverage. Neither order nor a
shorter junction predicts experimental performance. A truncated search leaves
part of the declared space unresolved. See [search interpretation](../discovery/overview.md).

## How do local junctions become a construction?

A local solution describes a possible junction, not the entire molecule.
Composition checks selected junctions together with the source, adapters,
primers, fragment-removal program, and endpoint requirements. Missing annealing
sequence or incompatible materials must reject that proposed construction.

For the supported linear-source route, the modeled sequence of steps is:

```text
source ssDNA + primers → source duplex
    → cleavage → strand separation → fragment selection
    → foldback and required adapter pairing → covalent joins → ssDNA hairpin
    → optional PCR duplex → optional end-generating cleavage
```

Nicking breaks one backbone; it does not itself remove a fragment. Separation
and selection are distinct steps. PCR derives expected strands from declared
primer bindings; HOP does not predict amplification efficiency.

The requested endpoint determines which steps and materials are required.
A direct ssDNA hairpin does not acquire adapter, PCR, or end-generation
requirements merely because another endpoint needs them. For material and
request examples, use the [construction guide](../guides/compile-construction.md)
or [check a named method](../guides/resolve-production-method.md).

## What can you conclude?

Choose against your requirements first: available enzymes, permitted product
ends, pairing rules, and the materials you can supply or allow HOP to derive.
Then compare complete candidates using an explicit preference, such as less
retained construction sequence. An example's particular end sequence is not
a requirement for other designs. See the [construction guide](../guides/compile-construction.md)
for filtering, sorting, inspecting, and selecting alternatives.

A complete candidate can be found before a search is exhausted. Its completion
means that its declared molecular requirements are satisfied; it does not mean
that every alternative was examined or that this candidate is the shortest.
Keep the candidate's completeness separate from the search's coverage.

A successful computation supplies exact sequence and processing expectations.
[Verification](../provenance/overview.md) checks that the saved result follows
from its inputs. It does not establish recovery, folding, cleavage efficiency,
ligation efficiency, or biological activity. Defined cohesive ends also need
a separate compatibility check against the intended cloning destination.

Experimental protocols, tubes, controls, and observations belong in the
researcher's laboratory records, not in a computed molecular specification.
