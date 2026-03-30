# UI Copy Tone

All user-facing text in this app follows a casual, playful, lowercase tone. When writing or editing UI copy (button labels, headings, empty states, snackbar messages, dialog titles, helper text), follow these rules:

## General

- **Lowercase everything** — button labels, nav items, headings, dialog titles, empty states. Exception: proper nouns like "PDA".
- **Friendly, direct phrasing** — talk to people like they're in the group, not like they're filling out a government form.
- **Use em dashes (—) instead of periods** for joining clauses in body text.
- **Drop trailing periods** on single-sentence copy.

## Emoji

- Use sparingly — empty states and success confirmations, not on every button.
- Preferred emoji: 🌿 (empty/quiet states), 🌱 (confirmations/new beginnings), 🎉 (celebrations/approvals).

## Error Messages

- Casual but clear: `'couldn't load events — try refreshing'`, not `'Failed to load events'`.
- Never expose raw error objects to users (`$e`). Use a friendly fallback.
- Keep destructive action confirmations ("This cannot be undone.") clear and unambiguous — no cutesy rewrites.

## Examples

| Category | Bad | Good |
|----------|-----|------|
| Button | `'Submit Request'` | `'submit request'` |
| Nav | `'Calendar'` | `'calendar'` |
| Empty state | `'No events'` | `'nothing on today 🌿'` |
| Error | `'Failed to update RSVP: $e'` | `'couldn't update your rsvp — try again'` |
| Success toast | `'Name updated'` | `'name updated ✓'` |
| Dialog title | `'Edit Name'` | `'edit name'` |
| Body text | `'You need to be logged in to add events.'` | `'you need to be logged in to add events — pop in your number and we'll sort you out'` |
| Confirmation | `'Request received!'` | `'request received! 🌱'` |
| RSVP | `'Attending'` | `'i'm going'` |
| Destructive | `'Delete "Event"? This cannot be undone.'` | Keep as-is — clarity over cuteness |

## Scope

- **Public + member screens**: full playful treatment.
- **Admin screens**: lighter touch — lowercase and friendly empty states, but keep action labels functional.
- **Validation errors** (`'Required'`, `'At least 8 characters'`): keep clear and unambiguous.
- **Form field labels** (`'Display name'`, `'Password'`): keep standard casing for readability.
