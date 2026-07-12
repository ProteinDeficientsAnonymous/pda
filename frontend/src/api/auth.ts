import { useMutation } from '@tanstack/react-query';

import type { ConsentTypeValue } from '@/models/consent';
import { normalizePermissions } from '@/models/permissions';
import type { Role, User } from '@/models/user';
import { CalendarFeedScope, type CalendarFeedScopeValue } from '@/models/user';

import { apiClient, authClient, getCurrentAccessToken } from './client';

// --- Wire types (snake_case, server-shaped). ----------------------------------

interface WireRole {
  id: string;
  name: string;
  is_default: boolean;
  permissions: string[];
}

interface WireUser {
  id: string;
  phone_number: string;
  display_name: string;
  first_name?: string;
  last_name?: string;
  full_name?: string;
  nickname?: string;
  email?: string;
  bio?: string;
  pronouns?: string;
  is_superuser?: boolean;
  is_staff?: boolean;
  needs_onboarding: boolean;
  needs_password_reset?: boolean;
  needs_guidelines_consent?: boolean;
  needs_sms_consent?: boolean;
  show_phone?: boolean;
  show_email?: boolean;
  week_start?: 'sunday' | 'monday';
  calendar_feed_scope?: CalendarFeedScopeValue;
  profile_photo_url?: string;
  photo_updated_at?: string | null;
  roles: WireRole[];
}

interface TokenOut {
  // No `refresh`: the refresh token arrives via the httpOnly cookie, never the body.
  access: string;
}

interface AccessOut {
  access: string;
}

// --- Mapping helpers. ---------------------------------------------------------

function mapRole(r: WireRole): Role {
  return {
    id: r.id,
    name: r.name,
    isDefault: r.is_default,
    permissions: normalizePermissions(r.permissions),
  };
}

function mapUser(u: WireUser): User {
  return {
    id: u.id,
    phoneNumber: u.phone_number,
    firstName: u.first_name ?? '',
    lastName: u.last_name ?? '',
    fullName: u.full_name ?? u.display_name ?? '',
    nickname: u.nickname ?? '',
    email: u.email ?? '',
    bio: u.bio ?? '',
    pronouns: u.pronouns ?? '',
    isSuperuser: u.is_superuser ?? false,
    isStaff: u.is_staff ?? false,
    needsOnboarding: u.needs_onboarding,
    needsPasswordReset: u.needs_password_reset ?? false,
    needsGuidelinesConsent: u.needs_guidelines_consent ?? false,
    needsSmsConsent: u.needs_sms_consent ?? false,
    showPhone: u.show_phone ?? false,
    showEmail: u.show_email ?? false,
    weekStart: u.week_start ?? 'sunday',
    calendarFeedScope: u.calendar_feed_scope ?? CalendarFeedScope.All,
    profilePhotoUrl: u.profile_photo_url ?? '',
    photoUpdatedAt: u.photo_updated_at ?? null,
    roles: u.roles.map(mapRole),
  };
}

// --- Endpoints. ---------------------------------------------------------------

export async function login(
  phoneNumber: string,
  password: string,
): Promise<{ access: string; user: User }> {
  const { data } = await authClient.post<TokenOut>('/api/auth/login/', {
    phone_number: phoneNumber,
    password,
  });
  const user = await fetchMeWithToken(data.access);
  return { access: data.access, user };
}

export async function magicLogin(token: string): Promise<{ access: string; user: User }> {
  // Forward the current access token (if any) so the backend's cross-user
  // guard can detect that a different user is already signed in and reject
  // the link rather than silently swapping sessions.
  const current = getCurrentAccessToken();
  const config = current ? { headers: { Authorization: `Bearer ${current}` } } : undefined;
  const { data } = await authClient.get<TokenOut>(`/api/auth/magic-login/${token}/`, config);
  const user = await fetchMeWithToken(data.access);
  return { access: data.access, user };
}

export async function restoreSession(): Promise<{ access: string; user: User } | null> {
  // The refresh cookie is sent automatically. If it's missing/invalid, /refresh/
  // returns 401 and we treat the session as gone.
  try {
    const { data } = await authClient.post<AccessOut>('/api/auth/refresh/', {});
    const user = await fetchMeWithToken(data.access);
    return { access: data.access, user };
  } catch {
    return null;
  }
}

export async function logout(): Promise<void> {
  try {
    await authClient.post('/api/auth/logout/');
  } catch {
    // Idempotent; server-side clear isn't critical if the client already forgot.
  }
}

export async function fetchMe(): Promise<User> {
  const { data } = await apiClient.get<WireUser>('/api/auth/me/');
  return mapUser(data);
}

async function fetchMeWithToken(access: string): Promise<User> {
  // Used during login/magic-login/refresh before the store has the token yet.
  const { data } = await authClient.get<WireUser>('/api/auth/me/', {
    headers: { Authorization: `Bearer ${access}` },
  });
  return mapUser(data);
}

export async function completeOnboarding(payload: {
  newPassword: string;
  displayName?: string | undefined;
  email?: string | undefined;
  pronouns?: string | undefined;
  consentTypes?: ConsentTypeValue[] | undefined;
}): Promise<User> {
  const { data } = await apiClient.post<WireUser>('/api/auth/complete-onboarding/', {
    new_password: payload.newPassword,
    display_name: payload.displayName,
    email: payload.email,
    pronouns: payload.pronouns,
    consent_types: payload.consentTypes ?? [],
  });
  return mapUser(data);
}

export async function acceptConsents(consentTypes: ConsentTypeValue[]): Promise<User> {
  // records the given consents; accepting "guidelines" clears the hard login gate
  const { data } = await apiClient.post<WireUser>('/api/auth/accept-consents/', {
    consent_types: consentTypes,
  });
  return mapUser(data);
}

export async function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  await apiClient.post('/api/auth/change-password/', {
    current_password: currentPassword,
    new_password: newPassword,
  });
}

export interface ProfileUpdate {
  displayName?: string;
  nickname?: string;
  email?: string;
  bio?: string;
  pronouns?: string;
  showPhone?: boolean;
  showEmail?: boolean;
  weekStart?: 'sunday' | 'monday';
  calendarFeedScope?: CalendarFeedScopeValue;
}

export async function updateProfile(patch: ProfileUpdate): Promise<User> {
  // Omit undefined so PATCH doesn't clobber fields that weren't explicitly set.
  const body: Record<string, unknown> = {};
  if (patch.displayName !== undefined) body.display_name = patch.displayName;
  if (patch.nickname !== undefined) body.nickname = patch.nickname;
  if (patch.email !== undefined) body.email = patch.email;
  if (patch.bio !== undefined) body.bio = patch.bio;
  if (patch.pronouns !== undefined) body.pronouns = patch.pronouns;
  if (patch.showPhone !== undefined) body.show_phone = patch.showPhone;
  if (patch.showEmail !== undefined) body.show_email = patch.showEmail;
  if (patch.weekStart !== undefined) body.week_start = patch.weekStart;
  if (patch.calendarFeedScope !== undefined) body.calendar_feed_scope = patch.calendarFeedScope;
  const { data } = await apiClient.patch<WireUser>('/api/auth/me/', body);
  return mapUser(data);
}

export async function uploadProfilePhoto(file: File): Promise<User> {
  const formData = new FormData();
  formData.append('photo', file, file.name);
  const { data } = await apiClient.post<WireUser>('/api/auth/me/photo/', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return mapUser(data);
}

export async function deleteProfilePhoto(): Promise<User> {
  const { data } = await apiClient.delete<WireUser>('/api/auth/me/photo/');
  return mapUser(data);
}

// --- request login link -----------------------------------------------------

export type RequestLoginLinkDelivery = 'email' | 'admin' | 'cooldown';

interface RequestLoginLinkOut {
  detail: string;
  delivery: RequestLoginLinkDelivery;
}

export function useRequestLoginLink() {
  // Endpoint always returns 200 (anti-enumeration). The `delivery` field
  // distinguishes "we emailed you" from "an admin will follow up" so the
  // UI can render honest copy — the unknown-phone case is bundled into the
  // admin path so the response shape doesn't reveal whether the account
  // exists when no email was sent.
  return useMutation({
    mutationFn: async (phoneNumber: string) => {
      const { data } = await authClient.post<RequestLoginLinkOut>(
        '/api/community/request-login-link/',
        { phone_number: phoneNumber },
      );
      return data;
    },
  });
}
