// Consent registry — the single source of truth for the kinds of consent the
// app collects. Mirrors the backend ConsentType registry (users/_consents.py).
//
// To add a consent type (e.g. an email policy): add an entry here plus the
// matching backend registry entry. Both consent collection points
// (OnboardingScreen, ConsentScreen) render and submit through this registry, so
// neither needs per-type branching.

import type { User } from './user';

export const ConsentType = {
  Guidelines: 'guidelines',
  Sms: 'sms',
} as const;
export type ConsentTypeValue = (typeof ConsentType)[keyof typeof ConsentType];

export interface ConsentDescriptor {
  type: ConsentTypeValue;
  // Whether this consent is still outstanding for the given user.
  needs: (user: User) => boolean;
  // Checkbox copy. `linkLabel` links to `linkTo`; `before`/`after` wrap it.
  before: string;
  linkLabel: string;
  linkTo: string;
  after?: string;
}

// Order is the order checkboxes render in.
export const CONSENT_REGISTRY: readonly ConsentDescriptor[] = [
  {
    type: ConsentType.Guidelines,
    needs: (u) => u.needsGuidelinesConsent,
    before: 'i have read and agree to the ',
    linkLabel: 'community guidelines',
    linkTo: '/guidelines',
    after: ' and community agreements',
  },
  {
    type: ConsentType.Sms,
    needs: (u) => u.needsSmsConsent,
    before: 'i agree to the ',
    linkLabel: 'sms policy',
    linkTo: '/sms-policy',
  },
];

// The consents still outstanding for this user, in registry order.
export function missingConsents(user: User | null): ConsentDescriptor[] {
  if (!user) return [];
  return CONSENT_REGISTRY.filter((c) => c.needs(user));
}
