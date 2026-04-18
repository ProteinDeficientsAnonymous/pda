// Auth endpoint callers. Returns are shaped for the auth store, not raw axios
// responses — centralizes the mapping from backend snake_case to frontend camelCase.

import { apiClient, authClient } from './client';
import type { User, Role } from '@/models/user';

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
  email?: string;
  bio?: string;
  is_superuser?: boolean;
  is_staff?: boolean;
  needs_onboarding: boolean;
  show_phone?: boolean;
  show_email?: boolean;
  week_start?: 'sunday' | 'monday';
  profile_photo_url?: string;
  photo_updated_at?: string | null;
  roles: WireRole[];
}

interface TokenOut {
  access: string;
  refresh: string;
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
    permissions: r.permissions,
  };
}

function mapUser(u: WireUser): User {
  return {
    id: u.id,
    phoneNumber: u.phone_number,
    displayName: u.display_name,
    email: u.email ?? '',
    bio: u.bio ?? '',
    isSuperuser: u.is_superuser ?? false,
    isStaff: u.is_staff ?? false,
    needsOnboarding: u.needs_onboarding,
    showPhone: u.show_phone ?? false,
    showEmail: u.show_email ?? false,
    weekStart: u.week_start ?? 'sunday',
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
  const { data } = await authClient.get<TokenOut>(`/api/auth/magic-login/${token}/`);
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
}): Promise<User> {
  const { data } = await apiClient.post<WireUser>('/api/auth/complete-onboarding/', {
    new_password: payload.newPassword,
    display_name: payload.displayName,
    email: payload.email,
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
  email?: string;
  bio?: string;
  showPhone?: boolean;
  showEmail?: boolean;
  weekStart?: 'sunday' | 'monday';
}

export async function updateProfile(patch: ProfileUpdate): Promise<User> {
  // Omit undefined so PATCH doesn't clobber fields that weren't explicitly set.
  const body: Record<string, unknown> = {};
  if (patch.displayName !== undefined) body.display_name = patch.displayName;
  if (patch.email !== undefined) body.email = patch.email;
  if (patch.bio !== undefined) body.bio = patch.bio;
  if (patch.showPhone !== undefined) body.show_phone = patch.showPhone;
  if (patch.showEmail !== undefined) body.show_email = patch.showEmail;
  if (patch.weekStart !== undefined) body.week_start = patch.weekStart;
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
