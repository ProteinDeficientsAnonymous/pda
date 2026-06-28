# Task — issue #588
**Goal:** Add CLAUDE.md rule: avoid verbose comments, only comment when code doesn't explain itself
**Source:** label
**Labels:** auto,chore,p2
**Acceptance criteria:** see issue #588 body.

## Pipeline stage
review

## Restart count
0

## Progress log
- dispatched
- pickup: read task + issue #588; no `explore` label -> implement pipeline
- triage: actionable as scoped; add `### comments` rule under `## Standards` in CLAUDE.md
- work: added comments rule (no verbose/redundant comments; comment only non-obvious why; no what-restating; no multi-line blocks)
- review: code-reviewer subagent round 1 -> no high/medium findings; clean
- ci: backend green (1032 passed, ty, complexity, schemas); frontend green in isolation (JoinScreen timeouts were machine-contention flakes, pass 10/10 alone); change is doc-only
