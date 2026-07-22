# Feature flags

A flag is a named on/off switch, defined in code, whose state is toggleable
per environment from the admin UI at `/admin/feature-flags`. A flag is
**temporary by default** — it exists to let a half-finished feature merge to
`main` and deploy dark, not to become a permanent config knob.

## Add a flag

1. Add one member to `FeatureFlag` in
   [`backend/community/models/choices.py`](../backend/community/models/choices.py),
   plus its default in `FLAG_DEFAULTS` right below it:

   ```python
   class FeatureFlag(models.TextChoices):
       EXAMPLE_FLAG = "example_flag", "Example flag"
       MY_NEW_THING = "my_new_thing", "My new thing"

   FLAG_DEFAULTS: dict[str, bool] = {
       FeatureFlag.EXAMPLE_FLAG: False,
       FeatureFlag.MY_NEW_THING: False,
   }
   ```

2. Add the matching member to `Feature` in
   [`frontend/src/models/featureFlags.ts`](../frontend/src/models/featureFlags.ts).
   The string value must equal the backend key exactly:

   ```ts
   export const Feature = {
     ExampleFlag: 'example_flag',
     MyNewThing: 'my_new_thing',
   } as const;
   ```

3. Consume it:

   | Where | How |
   |---|---|
   | Backend endpoint logic | `flag_enabled(FeatureFlag.MyNewThing)` |
   | Frontend component | `useFlag(Feature.MyNewThing)` → `boolean` |
   | Frontend route | `<Route element={<RequireFlag flag={Feature.MyNewThing} />}>` |

No migration, no admin data entry, no endpoint change. The read/write
endpoints and the admin screen are generic over the registry — a new member
just shows up as another toggle.

## Toggle it

Anyone with the `MANAGE_FEATURE_FLAGS` permission can flip a flag from
`/admin/feature-flags`, on **any** environment including production — there's
no environment block, only the permission check. This is deliberate: if
something a flag was guarding turns out broken in a way staging didn't catch,
it needs to be killable in prod immediately, without a deploy.

A flag with no DB row resolves to its code default. Toggling writes a
`FeatureFlagState` row for that key; deleting the row (or never creating one)
falls back to the default again.

## Remove a flag

Once a feature has fully launched (or been abandoned), delete it:

1. Delete the member from `FeatureFlag` (backend) **and** `Feature`
   (frontend).
2. TypeScript and Python now fail to compile at every remaining call site —
   the compiler hands you the exact cleanup list. Delete the `useFlag`/
   `flag_enabled`/`RequireFlag` checks it flags.
3. Any leftover `FeatureFlagState` row for that key is inert — resolution
   only reads rows for keys still in the registry. No migration is needed to
   remove a flag; a stray row can be dropped later or just ignored.

## Shipping a flagged feature to production

Prod evaluates flags the same way every environment does — from
`FLAG_DEFAULTS`, overridden by any `FeatureFlagState` row. To turn a feature
on for everyone:

- **Fast path:** flip its entry in `FLAG_DEFAULTS` to `True` and deploy. Every
  environment without an explicit override picks up the new default.
- **Immediate path:** toggle it on directly from `/admin/feature-flags` on
  production (see above) — no deploy needed, useful for a timed launch.

Once it's stable, delete the flag (previous section) so it doesn't linger as
dead code.
