# ADR 0001: Event-driven membership status transitions

## Status

Accepted (membership). Join-request status and event-shaped HTTP/MCP payloads are follow-up.

## Context

`MembershipStatus` used to change via ad hoc field writes and open-ended
`set_membership_status` assignment. That made illegal paths easy and scattered
the rules across call sites.

## Decision

Model the membership lifecycle as a small event-driven state machine on `User`:

1. Explicit status + event enums (`MembershipStatus`, `MembershipEvent`).
2. One allowed-transition table: `(current, event) → next`.
3. One apply path that validates the edge, stamps status/actor/time, and rejects
   with `InvalidStateTransition` (audited after rollback).
4. Named methods on the model (`approve_membership`, `archive`, …) as the public
   API; they call the apply path.
5. Application code loads → fires a named method → saves → runs side effects
   (email, roles, provisioning) outside the machine.
6. Creates set an initial status directly; they are not transitions.

Admin PATCH still uses pause booleans (`guidelines_paused`, `attendance_paused`);
those map to named transition methods at the boundary. A later change can teach
HTTP/MCP decision endpoints to accept events directly, and can machine
`JoinRequestStatus` the same way.

## Consequences

- Invalid membership transitions are impossible at the model boundary (for call
  sites that use the named methods).
- Call sites read as business intent (`approve`) rather than assignment.
- Orchestration files stay responsible for side effects; the machine stays pure
  of I/O.
- Seed data and tests may still assign status when constructing fixtures.

## References

- Lifecycle map: [user-states.md](../user-states.md)
- Pattern notes: Protean “Model Aggregate Lifecycle as a State Machine”;
  transitions as deterministic `(state, event)` pairs (XState / Fowler).
