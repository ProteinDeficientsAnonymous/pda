# User capabilities

What each user type can do, as the backend enforces it. For how people move between types, see [user-states.md](user-states.md).

- **visitor** — not signed in.
- **public rsvper** — `membership_status=none`; RSVP'd through the public form, uses a `/my-rsvps` token link, never signs in.
- **limited** — signed in without full access: tentative or attendance-paused. Both get the same access, though attendance-paused users still hold membership (`is_member`) and the member role.
- **member** — `membership_status=active_member`. Elevated roles add the permissions further down.

Guidelines-paused, archived and `none` users can't sign in. They can still browse as a visitor. A guidelines-paused number is sent to login from the public RSVP form and told "already a member" by the join form; login only says they're paused after the right password, so nobody learns it from a phone number alone.

A rejected applicant can't sign in or public-RSVP (the form and `/my-rsvps` both refuse with the generic `rsvp_could_not_be_created`) until they submit a new join request. An archived user can submit the join form again; marking that request tentative or approving it restores the account.

## Events

| | visitor | public rsvper | limited | member |
|---|---|---|---|---|
| see public events | ✅ | ✅ | ✅ | ✅ |
| see members-only events | ❌ | ❌ | official/club only | ✅ |
| see invite-only events | ❌ | ❌ | if invited | if invited, or hosting |
| see location, whatsapp/partiful links | ❌ | official events open to public RSVP, via token link | official/club only | ✅ |
| RSVP | official public events, via public form (becomes a public rsvper); not after a rejected join request | same, managed at `/my-rsvps` | official/club only | ✅ |
| see guest list | ❌ | events they RSVP'd to | events they RSVP'd to | events they RSVP'd to |
| comment | ❌ | events they RSVP'd to | events they RSVP'd to | events they RSVP'd to |
| create events | ❌ | ❌ | ❌ | community + drafts; official/club need a tag permission |
| co-host | ❌ | ❌ | ❌ | ✅ |
| download one event's `.ics` | public fields | public fields | full, even for community events (see open questions) | full |

On a community event, a limited user sees exactly what a visitor sees and can't act on it (`community/events/limited_access.py`). Hosts, co-hosts and `manage_events` holders can always see guests and comment.

## People

| | visitor | public rsvper | limited | member |
|---|---|---|---|---|
| member directory | ❌ | ❌ | ❌ | ✅ |
| member profiles | ❌ | ❌ | ❌ | ✅ |
| member search (co-host / invite picker) | ❌ | ❌ | ✅ | ✅ |

Directory and search both respect each member's `show_phone`, `show_email`, `show_birthday` and `hide_last_name`.

## Content and account

| | visitor | public rsvper | limited | member |
|---|---|---|---|---|
| public pages, FAQ, public surveys | ✅ | ✅ | ✅ | ✅ |
| members-only pages and surveys | ❌ | ❌ | ✅ | ✅ |
| event feedback survey | per-attendee token link | per-attendee token link | per-attendee token link | per-attendee token link |
| calendar subscription feed | ❌ | ❌ | ✅ | ✅ |
| weekly / monthly digest emails | ❌ | ❌ | ✅ | ✅ |
| hold roles | ❌ | ❌ | attendance-paused keep the member role | ✅ |

"Members-only" pages and surveys only check that someone is signed in, so limited users see them too.

## Elevated permissions

Granted through roles; only members can hold roles. The admin role has every permission.

| Permission | Unlocks |
|---|---|
| `create_user` | create member accounts directly |
| `manage_users` | edit, pause, attendance-pause, archive and hard-delete members; assign roles |
| `manage_roles` | create, edit and delete roles |
| `approve_join_requests` | vet join requests: tentative, approve, reject, un-reject |
| `manage_events` | edit any event, see every guest list and questionnaire response, comment anywhere |
| `tag_official_event` / `tag_club_event` | create or retag official / club events |
| `edit_guidelines`, `edit_faq`, `edit_homepage`, `edit_join_questions`, `edit_speech_template` | edit that content |
| `manage_surveys` | create and edit surveys |
| `manage_documents` | read and edit internal docs |
| `import_payments` | import and verify cash app payments |

Source of truth: `backend/users/permissions.py` (`PermissionKey`), mirrored in `frontend/src/models/permissions.ts`.

## Open questions

- The calendar feed doesn't apply the limited-user filter. A limited user can mint a feed token, and the feed then includes every active event (except invite-only events they aren't on) with full location and links (`community/events/calendar.py`) ([#2246](https://github.com/ProteinDeficientsAnonymous/pda/issues/2246)).
- `/events/{id}/ics/` checks visibility but skips `event_viewer_for`, so a limited user gets location and links for a members-only community event by id — the event page itself hides them ([#2247](https://github.com/ProteinDeficientsAnonymous/pda/issues/2247)).
- `/users/search/` isn't gated like the directory and profiles, so limited users can search members by name and see phone numbers members chose to show (`users/_management.py` `search_users`) ([#2248](https://github.com/ProteinDeficientsAnonymous/pda/issues/2248)).
