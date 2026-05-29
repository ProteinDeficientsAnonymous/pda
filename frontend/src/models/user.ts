// Hand-written until `pnpm types:api` is run against a live backend. When the
// generated types come online, swap these for `components['schemas']['UserOut']`
// narrowings in api/auth.ts — this file should disappear.

export const CalendarFeedScope = {
  All: 'all',
  Mine: 'mine',
} as const;
export type CalendarFeedScopeValue = (typeof CalendarFeedScope)[keyof typeof CalendarFeedScope];

export interface Role {
  id: string;
  name: string;
  isDefault: boolean;
  permissions: string[];
}

export interface User {
  id: string;
  phoneNumber: string;
  displayName: string;
  email: string;
  bio: string;
  isSuperuser: boolean;
  isStaff: boolean;
  needsOnboarding: boolean;
  // Set after consuming a self-service magic login link: the user authenticated
  // without a password and must set a new one (routes to /new-password).
  needsPasswordReset: boolean;
  showPhone: boolean;
  showEmail: boolean;
  weekStart: 'sunday' | 'monday';
  calendarFeedScope: CalendarFeedScopeValue;
  profilePhotoUrl: string;
  photoUpdatedAt: string | null;
  roles: Role[];
}

/**
 * Where a user must go to finish setting up their account before using the app,
 * or null if nothing is pending. SINGLE source of truth for this decision —
 * both OnboardingGate and MagicLoginScreen call this so they can't drift.
 *
 *   - needsOnboarding (admin-created, first-time) or needsPasswordReset
 *     (consumed a self-service login link) → must set a password.
 *   - /new-password only works when name AND email are already on file (it
 *     collects neither). Anyone missing either goes to /onboarding, which
 *     collects whatever's missing (legacy accounts approved before email was
 *     required land here).
 */
export function passwordSetupRedirect(user: User | null): '/new-password' | '/onboarding' | null {
  if (!user) return null;
  if (!user.needsOnboarding && !user.needsPasswordReset) return null;
  const hasNameAndEmail = user.displayName.length > 0 && !!user.email;
  return hasNameAndEmail ? '/new-password' : '/onboarding';
}
