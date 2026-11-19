# ADR 0001: Event-driven status transitions

## Status

Accepted

## Context

`MembershipStatus` and `JoinRequestStatus` used to change via ad hoc field writes
and target-status APIs (`set status to approved`). That made illegal paths easy
and scattered the rules across call sites.

## Decision

Model each lifecycle as a small event-driven state machine on the aggregate:

1. Explicit status + event enums.
2. One allowed-transition table: `(current, event) → next`.
3. One apply path that validates the edge, stamps status/actor/time, and rejects
   with `InvalidStateTransition` (audited after rollback).
4. Named methods on the model (`approve_membership`, `reject`, …) as the public
   API; they call the apply path.
5. Application code loads → fires a named method → saves → runs side effects
   (email, roles, provisioning) outside the machine.
6. HTTP/MCP decision endpoints accept an **event**, not a target status.
7. Creates set an initial status directly; they are not transitions.

## Consequences

- Invalid transitions are impossible at the model boundary.
- Call sites read as business intent (`approve`) rather than assignment.
- Orchestration files stay responsible for side effects; the machine stays pure
  of I/O.
- Admin UIs and OpenAPI payloads must speak events (`approve`, `mark_tentative`,
  `reject`), while response bodies still report the resulting status.
- Seed data and tests may still assign status when constructing fixtures.

## References

- Lifecycle map: [user-states.md](../user-states.md)
- Pattern notes: Protean “Model Aggregate Lifecycle as a State Machine”;
  transitions as deterministic `(state, event)` pairs (XState / Fowler).
