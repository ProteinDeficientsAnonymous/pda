# Issue 1253: Payment Prefill Deep Links Research

## Current Implementation (Cash App)

**File:** `frontend/src/utils/paymentHandle.ts`

Cash App supports URL-based payment prefilling via:
- **Base URL:** `https://cash.app/$handle`
- **With amount:** `https://cash.app/$handle/AMOUNT` (path segment, not query param)
- **Example:** `https://cash.app/$alice/20` prefills $20 payment to @alice

**Current code:**
```typescript
export function toCashAppPayUrl(cashappLink: string, opts: { price?: string }): string {
  const base = toCashAppUrl(cashappLink);
  if (!base) return base;
  const amount = parseCashAppAmount(opts.price);
  if (amount === null) return base;
  return `${base}/${amount}`;
}
```

**Usage:** `EventMemberSection.tsx` (line 172) wires it only when feature flag `event_payment_confirmation` is on.

**Limitations:** Cash App does NOT support prefilling notes/memos via public URLs.

---

## Venmo Research

### URL Scheme Investigation

**Standard Venmo URLs:**
- Profile link: `https://venmo.com/u/USERNAME`
- Public payment page: `https://venmo.com/?txn=pay&recipients=USERNAME` (available on web, not documented as public API)

**Deep linking / Mobile app:**
- iOS: `venmo://paycharge?txn=pay&recipients=USERNAME` (undocumented, may not be stable)
- Android: Similar scheme, not officially documented

**Query Parameters Investigated:**
- `amount=X` — Venmo does NOT support prefilling amount via query param in documented URLs
- `note=X` or `description=X` — No public support for memo prefilling
- Venmo app requires user interaction to set amount; no "one-tap" payment support

### Conclusion: Venmo
**Feasibility:** Limited. Venmo's public web interface does NOT have documented URL parameters for prefilling amount or note. While profile links work (`https://venmo.com/u/USERNAME`), users must manually enter payment details. Deep linking via `venmo://` scheme is undocumented and not reliable.

**Recommendation:** Do NOT implement prefilled Venmo payments at this time. Keep as a plain profile link. If Venmo's API evolves or documentation clarifies, revisit.

---

## Zelle Research

### URL Scheme Investigation

**Banking Integration Only:**
- Zelle is not a standalone app; it's a fund transfer service operated by *The Clearing House* and embedded in US bank apps (Chase, Bank of America, Wells Fargo, etc.)
- No public Zelle website with payment links (unlike Cash App or Venmo)
- Each bank implements Zelle differently

**Deep Linking:**
- No public deep-link scheme for Zelle payments
- Bank-specific apps may support `bankname://zelle?...` but these are not standardized or documented
- Some banks allow SMS-based Zelle requests, but these are internal flows

**Web Payment Links:**
- Zelle does NOT publish a public web URL format for initiating payments
- No documented query parameters for amount, memo, or recipient prefilling
- Payment requests must be initiated within a user's banking app or via invitation emails

### Conclusion: Zelle
**Feasibility:** Not feasible. Zelle has no public URL scheme, web interface, or documented deep-linking support. Payment initiation is exclusively within banking apps and internal to each bank's platform.

**Why it's different from Cash App/Venmo:**
- Cash App & Venmo are standalone payment platforms with public web and mobile experiences
- Zelle is a backend clearing network, not a consumer-facing app
- There is no "send to @handle" like Venmo; Zelle requires account-to-account data (routing number, account number, or email tied to Zelle)

**Recommendation:** Do NOT attempt to create Zelle payment links. The current UI approach (storing `zelleInfo` as a text field, displaying as label) is the only viable integration.

---

## Summary Table

| Service | Web Link | Prefill Amount | Prefill Note | Status |
|---------|----------|-----------------|--------------|--------|
| Cash App | ✅ Yes | ✅ Yes (path) | ❌ No | ✅ Implemented |
| Venmo | ✅ Profile only | ❌ No | ❌ No | ⚠️ Plain link only |
| Zelle | ❌ No | ❌ No | ❌ No | ❌ Text-only info |

---

## Implementation Path (If Approved Later)

If Venmo adds prefill API support in the future:

1. Add `toVenmoPayUrl(venmoHandle: string, opts: { amount?: string; note?: string }): string` to `paymentHandle.ts`
2. Add tests for amount/note validation
3. Wire into `CostSection` similar to Cash App (line 172)
4. Gate behind feature flag (reuse or extend `event_payment_confirmation`)

**For this spike:** No code changes. Documentation only. Cash App already has the pattern in place. Venmo and Zelle remain unsupported for prefilling due to lack of public URL schemes.
