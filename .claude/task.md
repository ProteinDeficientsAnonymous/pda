# Task — issue #525
**Goal:** feat(public-rsvp): enforce non-members never hold a role + trustworthy role counts
**Source:** label
**Labels:** backend,RSVP & Attendance,auto
**Acceptance criteria:** see issue #525 body.

## Pipeline stage
done

## Restart count
1

## Progress log
- dispatched
- work: added m2m_changed pre_add guard (reject_role_for_non_member) on User.roles.through; added is_member=True to list_roles/delete_role counts; added TestNonMemberCannotHoldRole
- review: code-reviewer clean (no high); applied medium fixes (docstring note + member-swap/reverse-set tests). 23 tests pass.
- ci: backend make agent-ci passed (1026 tests, typecheck, complexity, schema); frontend lint/format/typecheck/types-check clean after pnpm install
- PR: https://github.com/ProteinDeficientsAnonymous/pda/pull/557 (draft)
