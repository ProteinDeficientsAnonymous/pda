# Task — issue #555
**Goal:** public-rsvp: recognize returning non-members and extend existing token on new RSVP
**Source:** label
**Labels:** backend,feature,auto,database,p1
**Acceptance criteria:** see issue #555 body.

## Pipeline stage
pickup
triage
work
review
ci

## Restart count
0

## Progress log
- dispatched
- triage: model-layer change only; public RSVP submission endpoints (stages 3/4) not built yet. Implementing issue_or_extend() on NonMemberRsvpToken to handle extend-vs-create. User get-or-create-by-phone (AC#1) belongs to the unbuilt endpoint; noted as out of scope here.
