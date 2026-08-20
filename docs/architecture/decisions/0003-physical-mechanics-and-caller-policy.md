---
doc_id: hop-adr-0003
title: ADR 0003 - Physical mechanics and caller policy
intent: Record the separation of molecular derivation, caller policy, and rendering.
audience:
  - maintainers
  - integrators
owner: HOP Design maintainers
status: accepted
last_verified: 2026-08-20
---

# ADR 0003: Physical mechanics and caller policy

## Context

Predecessor workflows combine physical pair/cut derivation, application
thresholds, processing-agent identity, workspace orchestration, and plotting.
Copying that shape would create a public package coupled to one private use
case and make physical results difficult to reuse or test independently.

## Decision

HOP owns pure foldback pairing, basal pair classification, and strand-state
projection from explicit typed inputs. Callers own application catalogs,
eligibility, and selection thresholds and pass them through versioned strict
contracts. `ResolvedHopSpec` is an explicit event integration boundary, not a
private catalog resolver. Renderers consume `WorkflowView` and cannot recompute
molecular state.

## Alternatives

A built-in application catalog would simplify one caller but turn private
identity and thresholds into package defaults. A plugin framework would defer
ownership questions while adding abstraction before a second implementation.
Letting renderers derive molecular state would create a second scientific
authority and allow figures to drift from plans.

## Consequences and reversal cost

Callers perform an explicit translation from their catalog and policy into HOP
requests. The standalone kernel and fixtures remain public-by-construction and
can be tested without neighboring repositories. Private parity translators are
temporary downstream code. Recombining policy with physics later would be a
breaking change to schemas, diagnostics, and migration ownership, so reversal
cost is high.
