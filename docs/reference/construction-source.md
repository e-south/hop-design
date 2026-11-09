# Construction source and material policies

This reference describes low-level inputs to [construction compilation](../guides/compile-construction.md).
For product-level authoring, start with [desired scaffolds](../guides/discover-product-scaffolds.md).

## Prepare the two authorities

Construction compilation requires two independent inputs:

1. a regular, nonsymlink JSON or YAML file with schema
   `hop.construction-source/v8`; and
2. a verified design-bundle directory produced by HOP.

The construction source declares the foldback request, an optional basal
request, the requested endpoint, how the source ssDNA and its preparation
primers are resolved, endpoint-dependent auxiliary materials, whole-route
constraints, and finite enumeration bounds. Its shape is:

```yaml
schema: hop.construction-source/v8
foldback: <hop.local-neighborhood-request/v7 mapping>
basal: <hop.local-neighborhood-request/v7 mapping or null>
composition:
  endpoint: ssdna_hairpin | adapter_ligated_hairpin | hairpin_pcr_duplex | clone_ready_duplex
  materialization:
    source_preparation:
      source_ssdna: <derive or fixed source-ssDNA policy>
      forward_primer: <derive, constrain, or fixed source-primer policy>
      reverse_primer: <derive, constrain, or fixed source-primer policy>
    adapter_ligation: <adapter policy for adapter_ligated_hairpin or omitted>
    endpoint_auxiliaries:
      adapter: <derive, constrain, or fixed adapter policy>
      forward_primer: <derive, constrain, or fixed endpoint-primer policy>
      reverse_primer: <derive, constrain, or fixed endpoint-primer policy>
  release: <exact oriented Type IIS endpoint release or null>
  whole_route_constraints: <intrinsic route constraints>
  enumeration:
    max_combinations: <positive integer>
    max_realizations: <positive integer>
```

Angle-bracketed values above describe required mappings; they are not literal
values to copy. Start from a complete example source under `examples/` and
consult the [schema reference](schemas.md) for supported document types and limits.
The public API reads the source file directly; no study package or internal
model import is required. Keep the design bundle outside the source document.
YAML anchors, aliases, and merge
keys are rejected. The source cannot author design, result, realization,
projection, output-path, timestamp, or environment identities.

Source preparation is an explicit modeled relation:

```text
source ssDNA + two source-preparation primers
    -> exact copied source duplex
```

The source ssDNA is the first external route material. The copied duplex is a
derived route state, not another material for the caller to provide. Source
primer annealing is resolved outside the payload and its terminal chemistry is
validated before the copied duplex can seed downstream construction.

`endpoint_auxiliaries` is separate and is required only for PCR-bearing
endpoints after the ssDNA hairpin has formed. Each nested policy has one exact
meaning:

- `derive`: HOP derives the adapter from the selected basal pairing segment or
  a primer from the exact PCR template at one caller-authored annealing length;
- `constrain`: HOP appends one explicit caller-supplied adapter or primer handle
  and chooses the shortest valid primer annealing length inside the declared
  inclusive range; and
- `fixed`: the caller supplies one exact material and HOP verifies its sequence,
  annealing relation, and terminal chemistry.

The adapter always preserves the selected basal pairing segment. A derived or
constrained forward primer binds within the invariant source-side construction
prefix, and its reverse counterpart binds within the adapter. Neither may
anneal across the payload. HOP performs no Tm, yield, or empirical ranking, and
does not generate a reusable handle that the caller did not specify.

To limit imperfect pairing, set `geometry_domain.max_noncanonical_pairs` in a
basal request. It counts G:T/T:G wobble and other mismatches across the declared
proximal `pairing_constraints`. For example, `2` allows at most two noncanonical
pairs while the ligation-adjacent position still requires a match. Omission
applies no aggregate cap. This caller-selected bound is not a prediction of
ligation efficiency; it does not relax recognition-site fidelity or apply to
distal adapter completion. At displaced nicks the proximal window and final
cohesive-end footprint need not coincide.

Basal discovery is deliberately local. It establishes the payload-proximal
nick, the exact proximal adapter pairs, any position-level source and adapter
base domains, the minimum full annealing extent, mismatch warnings, retained
overhead, and—for a clone-ready endpoint—the Type IIS action required later.
The future release is an obligation, not a sticky end asserted in the current
adapter state. Its `cohesive_end_sequence` may pin exact DNA or declare an
[IUPAC design domain](../discovery/overview.md#search-a-basal-cohesive-end-or-pin-it-to-a-destination).
Basal discovery does not invent the remaining annealing bases,
finalize the complete adapter, or claim a PCR product. Complete composition
must satisfy those obligations against the realized source scaffold and exact
endpoint materials.

The future release requires an explicit `payload_end_offset_bp`, independent
of the nick offset. It measures paired non-payload positions between the payload
and the near edge of the final overhang. Both complete release-side requirements
also declare this field. The side selected by the local action must agree with
the complete request. A zero gap excludes the overhang itself from the paired
count; it does not describe a zero-length end.

The source recognition placement follows the characterized action's cuts at
that gap. It does not follow the nick when only the nick is moved. Local search
intersects the independently placed recognition and end constraints. At complete
release, the exact cut union must still equal the verified design encoding;
HOP then measures each gap from the cuts to the design's payload features.

When compiling an exact design from selected local realizations, the clone-ready
basal arms cover the declared gap plus overhang length. Their exact source bases
and adapter bases must be determined by the local record or its future end
obligation. An undetermined adapter position requires an explicitly authored
design; the compiler does not choose an undeclared distal base. The PCR-only
design instead preserves the full local retained span.

Pairing position zero is the adapter base beside the nick, not the base beside
the payload. A displaced nick leaves an intervening source-derived segment;
those positions do not count toward adapter annealing. The local PCR accounting
view includes that segment plus the constrained adapter positions. It does not
measure the length of the final restriction-released insert or the complete
adapter. Later cohesive-end obligations include any source-derived bases before
the adapter begins; only overlapping adapter positions carry that future role.

PCR composition retains the source-derived bases between the basal nick and
the payload, together with their original complementary partners. The adapter
joins at the nick; it does not replace those retained partners. The resulting
design includes this intervening duplex segment, and the route records its
pairing and source lineage through copying. A locally feasible nick still needs
compatible source primers, a complete adapter, and valid processing states.

For PCR-bearing composition, the adapter keeps the locally selected proximal
pairs, including any permitted mismatches. Undeclared distal positions pair
canonically with the adjacent invariant source flank. All adapter modes accept
`distal_pairing_constraints` using the same position, pair-class, and base-domain
fields as the local basal constraints. Positions are zero-based from the
adapter's ligation end, strictly ascending, and must lie beyond the local
segment but inside the required annealing span. For example:

```yaml
adapter:
  mode: constrain
  three_prime_handle_sequence: GATCTG
  distal_pairing_constraints:
    - position_from_ligation: 6
      allowed_class: wobble
```

This requires G:T or T:G at position 6; it is not permission to change the
source base. Derivation must resolve one exact adapter base per position.
An ambiguous choice raises an input error: narrow `allowed_adapter_bases` or
provide a fixed adapter. No arbitrary mismatch is selected. A fixed adapter
must satisfy the declared constraints and remain canonical at undeclared
distal positions. HOP appends a requested handle after the pairing segment;
a fixed material can instead contain overlapping pairing and primer-binding
spans. The trajectory records every literal pair, including permitted wobbles
and mismatches, without predicting annealing or ligation performance.

If the selected source lacks enough upstream sequence, that exact composition
is rejected. For PCR-bearing endpoints, a `fixed` source may supply a longer
upstream flank while preserving the entire local basal sequence, payload, and
foldback source. HOP maps both junctions into that exact source, derives primer
binding and full adapter annealing there, and checks additional actionable
enzyme sites. This applies in either foldback-source orientation; it does not
alter a local realization or count the added flank as local junction overhead.

Fixed-source replay evaluates that supplied completion only. To search upstream
sequence for a PCR-bearing endpoint, use a constrained source policy. This
fragment belongs under `composition.materialization.source_preparation`:

```yaml
source_ssdna:
  mode: constrain
  upstream_sequence_spec: MAAAGTCTGAC
  five_prime_end: hydroxyl
  three_prime_end: hydroxyl
```

The pattern precedes the unchanged basal source flank in the payload-forward
frame. HOP derives the physical source orientation from the foldback realization;
it does not ask the caller to reverse the pattern for a reverse-oriented foldback.
This synthetic pattern declares two upstream assignments, not two payloads.
Each assignment is checked for source and endpoint primer binding, complete
adapter pairing, and actionable enzyme sites. The resulting source material is
recorded as constrained, not caller-fixed.

To search lengths as well as bases, supply an explicit range and one IUPAC
base domain applied independently at every upstream position:

```yaml
source_ssdna:
  mode: constrain
  upstream_sequence_spec:
    min_length_nt: 10
    max_length_nt: 12
    base_spec: N
  five_prime_end: hydroxyl
  three_prime_end: hydroxyl
```

These are synthetic domain bounds, not preferred source lengths. A range
contains every permitted sequence at every inclusive length. HOP evaluates
lengths in ascending order and bases in A/C/G/T order within each length;
it does not stop at the first working length. A range has positive lengths
and an operational maximum of 1,000 nt. A source policy with `mode: derive`
instead evaluates the local source without an added upstream context.

Composition traverses foldback, basal, then upstream assignments. Its nominal
denominator includes all three domains. The existing
`max_combinations` and `max_realizations` bounds stop this traversal; a stopped
prefix is truncated even if every examined sequence failed. Accepted alternatives
remain distinct within geometry groups. Summary JSON and CSV bind each examined
assignment through `source_context_sequence`.

The string form supplies one finite, fixed-length domain; the range form
supplies a finite union of length-specific sequence domains. Neither form
provides constraint-directed cleanup-site placement. An unrestricted `N` domain
can be much larger than the declared execution budget, and a truncated prefix
does not establish absence at later lengths. HOP does not choose an unbounded
extension length, generate a reusable handle without constraints, or design
cleanup-nick tiling through this policy. A selected partition still
certifies its exact supplied source. No fixed primer is rewritten, no annealing
length is silently reduced, and no melting temperature or recovery is predicted.

The future release requirement records `recognition_material`:

- `source_duplex` (default): the Type IIS recognition sequence must coexist
  with the nickase recognition sequence in the source. Both motifs constrain
  the same bases before enumeration. The source site maps to the requested
  endpoint through copying; its presence does not apply Type IIS cleavage in
  the earlier nicking stage.
- `endpoint_material`: a later material, such as a PCR-primer tail, supplies
  the recognition sequence. Local discovery establishes the requested cut
  geometry and proximal end-sequence constraints, not source-site coexistence.
  Complete endpoint evaluation must still find and verify the actual sites.

These choices define different sequence-design questions and enter request
and result identity. A source-encoded request cannot be satisfied by silently
introducing its recognition site through a primer instead.

Representative policy shapes are:

```yaml
endpoint_auxiliaries:
  adapter:
    mode: constrain
    three_prime_handle_sequence: <explicit reusable DNA handle>
  forward_primer:
    mode: derive
    annealing_length_nt: <positive integer>
    five_prime_end: hydroxyl
  reverse_primer:
    mode: constrain
    min_annealing_length_nt: <positive integer>
    max_annealing_length_nt: <positive integer>
    five_prime_handle_sequence: <explicit DNA handle or empty string>
    five_prime_end: hydroxyl
```

A constrained primer deterministically uses its minimum declared annealing
length when that length fits the invariant binding region. A fixed adapter uses
`material`; a fixed endpoint primer uses `primer`. Those mappings use the exact
construction-material and PCR-primer contracts rather than free-form sequence
strings. A direct `ssdna_hairpin` omits `endpoint_auxiliaries` entirely.

Endpoint obligations fail closed:

| Endpoint | Source preparation | Basal request | Endpoint adapter and primers | Type IIS end generation |
| --- | --- | --- | --- | --- |
| `ssdna_hairpin` | required | omitted | omitted | omitted |
| `adapter_ligated_hairpin` | required | required | separate `adapter_ligation` policy; no endpoint PCR primers | omitted |
| `hairpin_pcr_duplex` | required | required | required | omitted |
| `clone_ready_duplex` | required | required local boundary authority | required | required by the endpoint release request |

The foldback and basal requests, when both are present, must describe the same
payload space. The exact payload in the verified design must belong to that
space; compilation never repairs or substitutes a payload base.
