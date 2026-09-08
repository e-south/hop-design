---
doc_id: hop-adr-0025
title: ADR 0025 - Center construction discovery on final payload geometry
intent: Fix the coordinate, route, discovery, validation, identity, and ownership semantics for payload-centered construction discovery.
audience:
  - maintainers
  - integrators
  - agent executors
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-29
doc_type: decision
amended_by: hop-adr-0028
---

# ADR 0025: Center construction discovery on final payload geometry

> Amended by [ADR 0028](0028-separate-foldback-boundary-from-nick-position.md):
> the payload/foldback boundary remains fixed while the nick may lie within the
> first retained foldback arm.

## Context

HOP already compiles exact hairpin designs, performs bounded component
discovery, resolves one named linear-source method, and verifies separate
design and method authorities. Those competencies use trustworthy molecular
primitives, but they do not yet share one construction-discovery contract.
Several route-local coordinate systems and historical component conventions
therefore risk making the source encoding, an enzyme arrangement, or one
method chronology appear to be the biological object.

The biological object is the intended duplex payload. Construction discovery
must preserve that object while finding peripheral sequence, enzyme, material,
and operation realizations that produce a requested endpoint. The scientist
surface for small substrate spaces remains valid and must not grow to expose
the construction ontology.

## Decision

### 1. Final-payload coordinates are authoritative

The caller authors one contiguous intended duplex payload in final-product
coordinates. The reference payload strand is stored 5-prime to 3-prime; its
aligned complement is derived unless a future route explicitly supports a
declared pair-state exception. The basal and foldback boundaries belong to
this final-payload view.

Internal positions are zero-based and half-open. A local offset of zero is
flush with the relevant payload boundary. Positive offsets move outward into
construction sequence. A route may not move a required junction into the
payload or change payload bases to make a construction route feasible.

Source coordinates are route-owned. Every route family provides an explicit
mapping from final-payload positions to one or more source-material segments;
contiguous encoding in one source interval is not a shared payload invariant.

### 2. Route family precedes endpoint

Construction requests follow this hierarchy:

```text
final payload
→ source-realization route family
→ requested endpoint
→ required neighborhoods, materials, operations, and states
```

The current family is `linear_source/v1`. Its supported endpoint vocabulary is
`ssdna_hairpin`, `hairpin_pcr_duplex`, and `clone_ready_duplex`. Endpoint choice
determines whether basal adapter capture, PCR, and end-generating cleavage are
required. Requirements from a later endpoint must not leak into a direct
single-stranded hairpin request.

### 3. Foldback and basal discovery share one local-neighborhood contract

Both local families use one request and result envelope. A request contains
the final payload, local family, route family, endpoint, family-specific target
geometry, required constraints, design preferences, a caller-provisioned
enzyme catalog, an explicit relaxation policy, and finite enumeration policy.

A result preserves the requested and achieved geometry, relaxation shell,
exact realizations, rejections, completion evidence, and reversible scientific
projections. Exact targets are examined before enabled discrete relaxation
shells. Reaching a bound before exhausting the declared domain is
`truncated`, never `infeasible`.

This advanced contract belongs behind the specialist discovery and method
surfaces, or one narrowly named advanced facade if implementation evidence
requires it. It is not added to `hop_design.spaces` or root-re-exported.

### 4. Foldback geometry uses explicit physical fields

The authoritative foldback target contains:

- `nick_offset_within_foldback_nt`;
- `loop_length_nt`; and
- `annealing_arm_length_bp`.

Compact plot labels may abbreviate those fields, but public schemas, prose,
and manuscript assets use the explicit meanings. Positional mnemonic shorthand
has no compatibility alias.

The target geometry is independent of its enzyme realization. Single-cleavage
and sequential terminus-plus-nick programs are concrete operation programs,
not permanent top-level route families. Every accepted realization preserves
the exact exposed strand, released and retained fragments, complementary arm,
closure bond, and achieved retained geometry.

### 5. Basal pairing is explicit and Type IIS processing is endpoint-dependent

The basal pairing state is ordered from the payload-proximal ligation
position outward. Every position retains its literal source and adapter bases,
pair classification, position from ligation, and any later end-projection role.
`match`, configured `wobble`, and declared `mismatch` are construction
bookkeeping, not thermodynamic or biological scores.

The current adapter-ligation route requires a canonical payload-proximal match
when the endpoint requires adapter capture. `ssdna_hairpin` does not invent
adapter, PCR, or Type IIS requirements. Type IIS processing and exact cohesive
ends belong only to `clone_ready_duplex` or another endpoint that explicitly
requests end generation. Directional or asymmetric ends are derived from exact
heteroduplex copying and cleavage states; they are not caller-assigned labels.

A basal geometry domain may constrain its future cohesive end with IUPAC DNA.
Its exact targets and future enzyme actions contain exact DNA only. Offset then
end-sequence traversal preserves distinct exact alternatives and checks the
offset-by-end cardinality before allocation. Complete composition accepts an
endpoint belonging to that domain, then requires the selected local action to
agree with the exact endpoint. This input grammar does not change the serialized
fields or the canonical bytes of exact requests and results.

### 6. Compactness is retained endpoint geometry

Construction sequence is classified as retained, transient, auxiliary, or
destination-associated. Compactness is measured in the requested endpoint by
the achieved local geometry and retained non-payload nucleotides. Recognition
sites, handles, and other precursor sequence removed before that endpoint do
not incur a compactness penalty.

Compactness is a design preference, not proof of a global minimum and not a
proxy for yield, enzyme count, or total precursor length. Realizations with
the same retained geometry remain distinct when their precursor, enzymes,
materials, stages, or intermediates differ.

### 7. Whole-route validation is staged and state-aware

A construction route is an ordered sequence of reaction stages. One stage may
contain concurrent operations, all resolved against the same accepted
pre-stage molecular state and applied as one non-conflicting event set. The
next stage consumes only the accepted post-stage state.

Recognition-like sequence invalidates a route only when it is physically
actionable in the state and stage where the enzyme is present. Strand state,
molecular membership, substrate requirements, prior cleavage, and declared
mismatches therefore affect whether a site is active. Any undeclared
physically actionable cleavage is a hard route failure.

Global composition also verifies payload preservation, local sequence
compatibility, operation order, fragment lineage, strand continuity, foldback
closure, endpoint-specific basal processing, and exact final encoding.

### 8. Exact realization identity is distinct from grouping

HOP preserves separate identities for a local realization, a complete
whole-route realization, the exact requested endpoint product, and achieved
geometry. A different precursor, enzyme arrangement, auxiliary material, or
ordered or concurrent stage program is a different realization even when the
final product or geometry is identical.

Achieved-geometry and final-product groups are presentation projections. Each
group records the complete member identities and multiplicity, and the groups
must reversibly cover the underlying realization set without omission or
deduplication.

### 9. Linear source is current; circularized source is an extension point

Only the linear-source construction family is implemented in this tranche. It
may encode the final payload in one contiguous source interval, but that fact
stays inside its source map.

The shared final-payload contract permits a future segmented source map and a
declared correlated pair-state exception. The current linear family may reject
those capabilities as unsupported. HOP does not add circularization chemistry,
search, figures, or claims until a separately accepted route decision defines
them.

### 10. Product, study, and manuscript have separate ownership

HOP owns molecular semantics, deterministic discovery and realization,
explicit states and transitions, identities, verification, and neutral tidy or
diagram-ready projections. It does not own experiment registries, wet-lab
records, evidence interpretation, manuscript claims, or publication figures.

Client studies own scientific questions, frozen HOP inputs and outputs,
experimental observations, interpretation, and promotion of candidate assets.
Manuscript systems own the premise, claim ceiling, evidence cutoff, accepted
snapshot imports, captions, and final composition. Downstream applications
consume HOP without defining this generic construction contract.

## Consequences

Construction discovery becomes payload-first, endpoint-explicit, and capable
of explaining every accepted route at nucleotide and molecular-state
resolution. Local modularity remains useful, but whole-route feasibility is a
separate composed claim. Scientific summaries can stay compact without erasing
alternatives.

This is an intentional pre-1.0 semantic break. New schemas use the accepted
vocabulary directly; retired field names and route assumptions receive no
aliases, fallback readers, or dual-write period. Existing immutable design and
method bundles remain historical authorities and are not silently
reinterpreted as the new staged construction result.

Implementation follows the roadmap phases after this decision. This ADR
freezes semantics; it does not claim that the new construction-discovery
schemas or route compiler already exist.
