# Construction usability principles

Help a scientist describe the hairpin or released insert they need, discover
complete scaffold options, form a deliberate comparison and retrieve exact
preparations. Whole-molecule choice comes before local construction identifiers.
Sequence-to-function and structured-substrate applications motivate this service;
HOP supplies molecular specifications, not predictions of experimental success.
Application hypotheses, assay observations and manuscript claims belong to callers.

## Current entrypoints

[Desired-scaffold discovery](../../guides/discover-product-scaffolds.md) owns
product dimensions, supported terminal forms and permitted preparation changes.
[Comparison briefs](../../guides/specify-a-comparison.md) own required membership,
stage-specific shared controls, method groups and prior-product/material reuse.
[Conditional exploration](../../guides/explore-conditional-variants.md) owns
supported neighborhood choices, regional preservation and continuous inspection
through the API, CLI and molecular viewport.
[The construction walkthrough](../../guides/design-a-construction.md) explains
one preparation and explicit alternatives. [The roadmap](roadmap.md) distinguishes
implemented capabilities, older versions and remaining work.

The earlier delivery sequence is implemented through those operations. Its
acceptance records remain in the linked delivery plans. This page owns durable
experience principles rather than another increment-by-increment status list.
The constrained molecular viewport is implemented. Its performance with unfamiliar users remains unestablished.

## Information architecture: intention, options, comparison, handoff

| User question | Public experience | Distinction to preserve |
| --- | --- | --- |
| What molecule do I want? | Intended endpoint and dimensioned whole hairpin or insert | Hairpin endpoint, intermediate and released duplex are different stages |
| What should vary? | Required dimensions or supported exact sequence members | Permitting a range is different from requiring every member |
| What must remain shared? | Explicit molecular properties at the intended comparison stage | Exact sequence, pairing and chemistry are separate properties |
| What may change in making it? | Permitted enzymes, material derivation and explicit reuse | Preserving a product does not preserve its preparation |
| What can I obtain within these bounds? | Complete molecular alternatives, examined failures and unexamined coverage | Local support is not complete-route admission; a stopped search is not impossibility |
| Which set serves my intention? | Required members, group relationships and accompanying changes | Display order is not a recommendation; modeled equality is not experimental equivalence |
| What do I take to the bench? | Explicit selection, exact oligos and chemistry, modeled steps and unresolved conditions | Material roles are not purchases, stock or measured readiness |

The happy path is **specify → discover complete options → compare at the intended
stage → select → retrieve preparations**. An explicit roster or local-junction
workflow remains available for users who need those controls; it should not be
a prerequisite to seeing whole-molecule alternatives.

## Progressive detail and molecular language

Show the intended product and comparison first. Expand preparation permissions
and diagnostic evidence when they explain a choice; retain internal coordinates
and exact identities in the underlying record. Required, achieved and unresolved
values need separate labels. An unsupported combination must not acquire a
plausible-looking default.

A terminal tract on a hairpin is not a later restriction-released end. Read each
exposed word in its own 5′→3′ direction with polarity and stage identified.
Paired end-to-payload distance excludes the overhang and is independent of nick
displacement. Loop size counts nucleotides; a drawn loop radius is not a physical
conformation prediction. Source length, paired extension and retained product
length must not share an ambiguous “size” control.

Enzyme catalogue membership, permission to use an action, compatibility with the
modeled route, reaction prerequisites and laboratory stock are different facts.
HOP may evaluate supplied molecular actions; it must not infer procurement or
experimental performance from their geometry.

## Explicit edits and trustworthy failure explanations

An edit creates a new request. Preserve the original failure or search boundary,
then identify the changed requirement or permission and its observed consequences.
A successful alternative demonstrates one way forward, not a uniquely necessary
or minimal repair. Invalid input and corrupt authority remain errors; expected
molecular rejection retains its stage, reason and evaluated scope.

A countable primer span, conflicting recognition window or achieved terminal
length can explain a failure spatially. Use recorded facts for that view; do not
invent a completed failed molecule. Negative reports should lead with the missing
requested member and examined cause while retaining detailed coverage underneath.
Silent bound relaxation, base substitution and implicit material redesign are
outside the contract.

## Molecular comparison and preparation comparison

Show changes in the resulting molecule separately from changes in making it.
Equal lengths do not imply equal sequence; different primers do not necessarily
imply extra substrate differences. A stage-specific control must compare that
stage's verified ancestry and molecular facts. Unavailable or ambiguous ancestry
is unassessed, not an agreement inferred from a picture.

Prior-product preservation permits alternative materials unless reuse is also
required. Exact reuse includes sequence and terminal chemistry. Shared properties
within a new set are separate from reuse of a previous preparation. Exact product
relationships must not be reduced to a schema label, display name or digest that
omits the property being compared.

## Figures and CLI/API interoperability

A dimensioned whole molecule establishes what the user obtains. Aligned details
make changed loop bases, extensions and terminal tracts countable. A stage pair
shows which differences persist after processing; a material strip identifies
what changes in preparation. The construction trace explains manufacture.
Use consistent orientation, region roles, nucleotide pitch and explicit crops.
Symmetric layout must not imply independent molecular feasibility.

Renderers consume verified projections and own layout, not a second derivation
of cuts, pairing or sequence origin. Keep essential labels readable at print
width without hover. Preserve exact identities, chemistry and tables in exported
handoffs; FASTA alone cannot encode the full material specification. No dashboard,
readiness score or aggregate quality metric is required for this experience.

CLI and API operations use the same request and result authorities. An
editor must export the exact request it executes and preserve identities through
retrieval and relocation. Do not implement a separate graphical molecular solver.
HOP remains usable without a private study, inventory service or assay system.

## Choose the next increment from a concrete task

Start from one user job that current public operations do not express or make
unnecessarily difficult. Freeze the intention and expected interpretation, test
valid and conflicting requests, retain failures and assistance, then propose a
bounded owner change. Separate an agent test from unfamiliar-user evidence and
both from laboratory performance. Broader searches and richer graphics need
separate acceptance criteria.

Use the [construction module map](../construction-map.md) to keep request
compilation, bounded execution, verified comparison and rendering decoupled.
A behavior change requires a failing regression at the owning layer. A structural
refactor preserves molecular meaning, failure scope, identities and serialization,
with explicit producer-version handling. Run focused checks, strict preflight and
the full verification endpoint, including source/distribution parity.
