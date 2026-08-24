---
doc_id: hop-adr-0006
title: ADR 0006 - Discovery, compilation, and assessment boundaries
intent: Separate catalog geometry search, molecular compilation, and optional artifact assessment.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-23
doc_type: decision
amended_by: hop-adr-0022
---

# ADR 0006: Discovery, compilation, and assessment boundaries

## Context

Predecessor hairpin workflows grew from experimental searches. They combine
processing-agent catalogs, recognition-site placement, brute-force sequence
construction, commercial ranking, workspace output, molecular compilation,
and structure plots. A direct port would make catalog exploration inseparable
from one application and would obscure which results are physical facts.

## Decision

HOP separates three stages:

1. **Discovery** evaluates caller-supplied processing-agent geometry under
   explicit targets and hard budgets. Results expose physical measurements,
   exact or nearest placement, blockers, and truthful truncation. Concrete
   sequence discovery is permitted only inside caller-authored IUPAC domains;
   HOP does not invent hidden filler or apply vendor and application rank.
2. **Compilation** consumes selected explicit events and derives the immutable
   molecular plan and bundle.
3. **Assessment** is an optional artifact-consumer layer. A structure predictor
   or alternate renderer may consume plan-owned sequences and link its result to
   a plan or bundle digest, but it cannot revise compile validity.

`search_nicking_placements` is the first discovery operation. For each
caller-supplied nicking agent it selects the orientation that nicks the declared
strand and reports whether the recognition site fits the target nick boundary,
paired tract, and available turn. The operation evaluates one finite geometry
per nicking agent. It orders hits by exactness, boundary displacement, required
precursor length, required turn length, and neutral identity. Callers may apply
separate documented selection policy afterward.

`search_foldback_precursors` is the second discovery operation. It consumes
one selected placement, replays that placement from its agent and target, and
intersects the recognition motif with explicit precursor and turn-extension
templates. It derives the returning foldback arm by reverse complement and
reports all additional recognition sites. Search-node and returned-hit budgets
remain distinct. This closes sequence-construction parity without accepting a
monolithic recipe or making unconstrained DNA completion an implicit default.

`search_basal_candidates` is an independent bounded enumeration over two
caller-authored four-nucleotide IUPAC arm domains. It reuses the canonical
basal classifier and supplied constraint profile, accounts for every examined
reserve or reject outcome, and returns a deterministic record order. ADR 0022
amends that historical wording: active candidate order is literal arm content
and content identity, not a physical or policy preference. It
does not infer release or nicking-agent geometry. Application target buckets,
control distance, mismatch-tier preference, vendor data, and procurement state
remain caller policy rather than HOP ranking inputs.

Route-required primers and adapters are vendor-neutral process materials, not
molecular states. This decision originally anticipated emitting them only after
generic derivation. [ADR 0010](0010-linear-source-method-materials.md) amended
that expectation for the implemented linear-source method: its request declares
six materials, and HOP validates their sequences, modifications, and bindings.
Procurement fields, application flanks, and experimental acceptance remain
downstream.

## Compatibility

This decision adds a public operation and strict supporting models without
changing any existing schema identifier or plan/bundle field. The operation
accepts `hop.processing-catalog/v1`; it adds no built-in experimental catalog.

## Consequences

New nicking or release agents can be supplied without changing HOP. Geometry
and sequence discovery remain reusable and testable without a workspace or
private study. Basal candidate enumeration is reusable without carrying a
scar-nick workspace or study profile. Basal processing and released-foldback
geometry now have separate bounded contracts. Concrete precursor
materialization and hairpin-junction route composition have their own bounded
contracts. Complete production-method resolution and predecessor differential
equality remain separate evidence gates. A general plugin registry remains
deferred until two independent artifact integrations establish a stable
protocol.
