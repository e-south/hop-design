# Scaffold comparison intent and explicit family revision

[ADR 0040](0040-explicit-comparison-controls.md) extends the current property
vocabulary, set summary and report. The version introduction below records this
preceding increment.

A comparative family needs three distinct contracts: intent, verified molecular
comparison, and explicit retrieval. A material change is not automatically a
change elsewhere in the product. A later coordinate can move while its regional
sequence remains unchanged.

`hop.construction-comparison/v2` adds a derived assessment of the existing exact
property comparisons: scaffold differences, shared scaffold properties,
coordinate movement, preparation changes and downstream endpoint changes.
Non-loop conservation is asserted only when every expected regional sequence is
available at the same hairpin stage. Missing or different-stage views do not
receive a shared-sequence claim. The assessment is rederived during validation
and bound into the v2 projection identity. Molecular authorities and their IDs
are unchanged. Historical v1 projections remain historical artifacts; regenerate
this non-authoritative view from their unchanged complete authorities.

`hop.construction-family-report/v2` includes that assessment and optional revision
provenance. The opening plate groups three whole hairpins with countable loop
crops, a preparation-change strip and one named representative continuation.
Detailed alignments remain in linked SVG/JSON; failed and unresolved requests
remain in the PDF and exact packet. Geometry equality is not sequence identity.
The human endpoint label is “released duplex insert”; `clone_ready_duplex` stays
the machine identifier. Retrieval discloses unresolved preparation conditions.

`hop.scaffold-comparison/v1` is a strict authoring brief: matching base-request
path and product, explicit `vary` roster, `hold` properties, optional geometry
permissions, optional requirements/material policies, display order and finite
bounds. It compiles to the existing `hop.construction-family/v1` authority.
Omitted values preserve the base; explicit replacements are recorded in the
portable brief. `requirements: null` explicitly clears scaffold requirements;
it does not clear other route constraints. `materials` replaces the complete
materialization policy. Unknown controls reject. Open-side extent remains an
achieved/shared property. The preview is now `hop.construction-family-preview/v2`
with effective product/material intent; canonical request identity is unchanged.

`reconcile_construction_family` verifies an independently completed request
against the exact expanded member request and selected local witnesses. It
publishes a new family, never mutates or resumes an existing capture. A same-
request continuation retains the member name; an edited request must add a new
name through an explicit revised family request. Every original member and its
request remain; unchanged outcomes are retained. Edited alternatives must fit
this shared-base family contract. A changed base material policy or endpoint
belongs to a separate family rather than rewriting retained requests. The full parent packet is
embedded under `history/parent/` and bound by its manifest digest. Revision
ancestry is verified recursively with a 16-revision bound, plus the existing
20,000-file and 512-MiB packet bounds.

Ordinary execution still emits `hop.construction-family-result/v1`; revision
emits v2 with explicit lineage. Both use the existing hashed family packet and
are admitted by the same member verifier. Each member preserves its original
producer; the revision records the current producer separately. Provenance is
not a signature. Neither operation discovers an alternative, relaxes a policy,
selects a set, ranks candidates or changes a molecular authority.
Tests cover explicit selection, edited alternatives, foreign requests/witnesses,
forged lineage, unchanged parent bytes and relocation of selected preparations.
