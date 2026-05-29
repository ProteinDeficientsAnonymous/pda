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
