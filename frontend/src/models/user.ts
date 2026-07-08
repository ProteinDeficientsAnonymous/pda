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
  firstName: string;
  lastName: string;
  fullName: string;
  nickname: string;
  email: string;
  bio: string;
  pronouns: string;
  isSuperuser: boolean;
  isStaff: boolean;
  needsOnboarding: boolean;
  // Set after consuming a self-service magic login link: the user authenticated
  // without a password and must set a new one (routes to /new-password).
  needsPasswordReset: boolean;
  // True until the user accepts the community guidelines (guidelines_consent_at
  // is null server-side). A hard gate — routes to /consent with no skip. Nobody
  // is grandfathered; existing members and admins must re-consent.
  needsGuidelinesConsent: boolean;
  needsSmsConsent: boolean;
  showPhone: boolean;
  showEmail: boolean;
  hideLastName: boolean;
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
 *
 * @param {User | null} user - the authenticated user, or null when signed out
 * @returns {'/new-password' | '/onboarding' | null} the setup route, or null
 *   when nothing is pending
 */
export function passwordSetupRedirect(user: User | null): '/new-password' | '/onboarding' | null {
  if (!user) return null;
  if (!user.needsOnboarding && !user.needsPasswordReset) return null;
  const hasNameAndEmail = user.firstName.length > 0 && !!user.email;
  return hasNameAndEmail ? '/new-password' : '/onboarding';
}

/**
 * Where a user must go to accept the community guidelines before using the app,
 * or null if they've already consented. The consent gate is HARD — no skip, no
 * dismiss — and applies to everyone (admins included). It runs only after any
 * password setup (passwordSetupRedirect) is resolved, so a brand-new user sets
 * their name + password first, then consents.
 *
 * @param {User | null} user - the authenticated user, or null when signed out
 * @returns {'/consent' | null} the consent route, or null when already consented
 */
export function consentRedirect(user: User | null): '/consent' | null {
  if (!user) return null;
  return user.needsGuidelinesConsent || user.needsSmsConsent ? '/consent' : null;
}

/**
 * The single gate screen a freshly-authenticated user must be sent to before
 * the app proper, or null if nothing is pending. Combines the password-setup
 * and consent gates in the SAME priority order OnboardingGate uses (password
 * setup first, then consent).
 *
 * Auth screens (LoginScreen, MagicLoginScreen) call this and navigate to the
 * result DIRECTLY rather than navigating to a protected route and leaning on
 * OnboardingGate to bounce. Leaning on the gate races: the target route (often
 * lazy-loaded) can render a blank Suspense fallback before the gate re-evaluates
 * with the new auth state, so a pending user sees a blank screen until refresh.
 * Navigating to the gate target up-front avoids that race entirely; the gate
 * remains the backstop for every later navigation.
 *
 * @param {User | null} user - the freshly-authenticated user, or null
 * @returns {'/new-password' | '/onboarding' | '/consent' | null} the gate route
 *   to navigate to, or null when the user may enter the app
 */
export function postAuthRedirect(
  user: User | null,
): '/new-password' | '/onboarding' | '/consent' | null {
  return passwordSetupRedirect(user) ?? consentRedirect(user);
}
