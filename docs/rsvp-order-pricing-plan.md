# RSVP order pricing (#2117)

Let hosts price the options of an RSVP question so each attendee's total follows what they ordered.

## Design

- **No new question type.** `select` (pick one tier) and `checkbox` (pick any items) already cover orders. A question becomes an order question when its options carry prices, so answer validation, rendering and the responses screen keep working unchanged.
- **`EventRsvpQuestion.option_prices`**: JSON list of integer cents, parallel to `options`. Empty means unpriced. When set it must match `options` in length, each value `0..10_000_00`, and only on `select`/`checkbox`.
- **Price locked at answer time.** `build_rsvp_answers` adds `price_cents` to each priced answer in the `questionnaire_responses` snapshot. The member path already keeps the previous snapshot when an answer is unchanged, so a later price edit doesn't move an existing attendee's total.
- **Total = sum of `price_cents`** over the attendee's snapshot. If a question was priced after someone answered it (no `price_cents` in their snapshot), the frontend falls back to the question's current prices.
- **`Event.price` is untouched.** Events with no priced question behave as today. For order events the total replaces `price` on the pay step; the host leaves `price` blank and writes `price_note` ("depends on your order"), which keeps the payment gate on (#2604: price or note + a payment method).

## Ordering with #2122

The #2122 stack (#2204 → #2205 → #2604, #2266) merges first. It makes `Event.price` a decimal, adds `price_note`, and adds migrations `0153_event_price_decimal` / `0154_event_accept_paypal`. Once it lands, merge main into these branches and renumber this feature's migration after theirs. Part 4 builds on #2604's pay-step and `formatPriceWithNote` changes.

## Stacked PRs (~200 lines each incl. tests)

1. **backend: priced options** — model field + migration, `option_prices` on `EventRsvpQuestionIn/Out`, validation, persist on create / sync / official defaults, include in the sync conflict check, regenerate OpenAPI types.
2. **backend: price snapshot** — `price_cents` per answer in `build_rsvp_answers`, tests for select, checkbox, unpriced and locked-price paths.
3. **frontend: host editor** — map `option_prices`, per-option price inputs in `EventRsvpQuestionDialog` behind a "price per option" toggle, send on sync.
4. **frontend: totals** — `orderTotalCents()` helper; live total on the RSVP form and payment step (also feeds the cash app pay link), total in my RSVP details, per-guest totals for hosts in the responses section.

## Out of scope (follow-ups)

- Cash App import matching against per-attendee totals (`community/cashapp` still parses `Event.price`).
- Plus-one pricing (the order total is what the attendee ordered; `has_plus_one` doesn't multiply it).
- MCP questionnaire tools setting `option_prices`.
- PayPal fee-inclusive totals (#2266 computes `paypal_price` from `Event.price` only).
- Counting priced questions in the payment gate, so an order event with no price or note still gates.
