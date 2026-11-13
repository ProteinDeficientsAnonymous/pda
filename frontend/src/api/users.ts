import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { normalizePermissions } from '@/models/permissions';
import {
  type Birthday,
  MembershipStatus,
  type MembershipStatusValue,
  type Veganniversary,
} from '@/models/user';

import { mapAttendedEvent, type WireAttendedEvent } from './attendedEvents';
import { apiClient } from './client';
import { memberAttendanceAnalyticsKey } from './memberAttendanceAnalytics';

// --- Domain types (camelCase) ------------------------------------------------

export interface MemberRole {
  id: string;
  name: string;
  isDefault: boolean;
  permissions: string[];
}

export interface Member {
  id: string;
  fullName: string;
  firstName: string;
  lastName: string;
  phoneNumber: string;
  email: string;
  bio: string;
  profilePhotoUrl: string;
  showPhone: boolean;
  showEmail: boolean;
  isMember: boolean;
  membershipStatus: MembershipStatusValue;
  isSuperuser: boolean;
  hasJoinedWhatsapp: boolean;
  needsOnboarding: boolean;
  loginLinkRequested: boolean;
  // Most recent event the member was checked in as attended. null if never.
  lastAttendedAt: Date | null;
  attendedCount: number;
  dateJoined: Date;
  roles: MemberRole[];
}

// --- Wire types (snake_case) -------------------------------------------------

interface WireRole {
  id: string;
  name: string;
  is_default: boolean;
  permissions: string[];
}

interface WireMember {
  id: string;
  first_name?: string;
  last_name?: string;
  full_name: string;
  phone_number: string;
  email?: string;
  bio?: string;
  profile_photo_url?: string;
  show_phone?: boolean;
  show_email?: boolean;
  is_member?: boolean;
  membership_status?: MembershipStatusValue;
  is_superuser?: boolean;
  has_joined_whatsapp?: boolean;
  needs_onboarding?: boolean;
  login_link_requested?: boolean;
  last_attended?: string | null;
  attended_count?: number;
  date_joined: string;
  roles: WireRole[];
}

function mapRole(r: WireRole): MemberRole {
  return {
    id: r.id,
    name: r.name,
    isDefault: r.is_default,
    permissions: normalizePermissions(r.permissions),
  };
}

function fromWire(w: WireMember): Member {
  return {
    id: w.id,
    fullName: w.full_name,
    firstName: w.first_name ?? '',
    lastName: w.last_name ?? '',
    phoneNumber: w.phone_number,
    email: w.email ?? '',
    bio: w.bio ?? '',
    profilePhotoUrl: w.profile_photo_url ?? '',
    showPhone: w.show_phone ?? true,
    showEmail: w.show_email ?? true,
    isMember: w.is_member ?? true,
    membershipStatus: w.membership_status ?? MembershipStatus.ActiveMember,
    isSuperuser: w.is_superuser ?? false,
    hasJoinedWhatsapp: w.has_joined_whatsapp ?? false,
    needsOnboarding: w.needs_onboarding ?? false,
    loginLinkRequested: w.login_link_requested ?? false,
    lastAttendedAt: w.last_attended ? new Date(w.last_attended) : null,
    attendedCount: w.attended_count ?? 0,
    dateJoined: new Date(w.date_joined),
    roles: w.roles.map(mapRole),
  };
}

// --- Queries / mutations -----------------------------------------------------

export const USERS_KEY = ['users'] as const;

export function useUsers(includeNonMembers = false) {
  return useQuery({
    queryKey: [...USERS_KEY, { includeNonMembers }] as const,
    queryFn: async () => {
      const config = includeNonMembers ? { params: { include_non_members: true } } : undefined;
      const { data } = await apiClient.get<WireMember[]>('/api/auth/users/', config);
      return data.map(fromWire);
    },
  });
}

export function useMemberAttendedEvents(userId: string) {
  return useQuery({
    queryKey: [...USERS_KEY, userId, 'attended-events'] as const,
    queryFn: async () => {
      const { data } = await apiClient.get<WireAttendedEvent[]>(
        `/api/auth/users/${userId}/attended-events/`,
      );
      return data.map(mapAttendedEvent);
    },
    enabled: userId !== '',
  });
}

export interface UpdateUserInput {
  phoneNumber?: string;
  firstName?: string;
  lastName?: string;
  email?: string;
  guidelinesPaused?: boolean;
  attendancePaused?: boolean;
  hasJoinedWhatsapp?: boolean;
}

export function useUpdateUser(userId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: UpdateUserInput): Promise<Member> => {
      const body: Record<string, unknown> = {};
      if (input.phoneNumber !== undefined) body.phone_number = input.phoneNumber;
      if (input.firstName !== undefined) body.first_name = input.firstName;
      if (input.lastName !== undefined) body.last_name = input.lastName;
      if (input.email !== undefined) body.email = input.email;
      if (input.guidelinesPaused !== undefined) body.guidelines_paused = input.guidelinesPaused;
      if (input.attendancePaused !== undefined) body.attendance_paused = input.attendancePaused;
      if (input.hasJoinedWhatsapp !== undefined) body.has_joined_whatsapp = input.hasJoinedWhatsapp;
      const { data } = await apiClient.patch<WireMember>(`/api/auth/users/${userId}/`, body);
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
      void qc.invalidateQueries({ queryKey: memberAttendanceAnalyticsKey });
    },
  });
}

export function useArchiveUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (userId: string): Promise<void> => {
      await apiClient.delete(`/api/auth/users/${userId}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

interface WireMagicLinkResult {
  detail: string;
  magic_link_token: string;
}

export interface MemberMagicLinkResult {
  detail: string;
  magicLinkToken: string;
}

export function useSendMemberMagicLink(userId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<MemberMagicLinkResult> => {
      const { data } = await apiClient.post<WireMagicLinkResult>(
        `/api/auth/users/${userId}/magic-link/`,
      );
      return { detail: data.detail, magicLinkToken: data.magic_link_token };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export function useUpdateMemberRoles(userId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (roleIds: string[]): Promise<Member> => {
      const { data } = await apiClient.patch<WireMember>(`/api/auth/users/${userId}/roles/`, {
        role_ids: roleIds,
      });
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

// --- Public member profile (any authed user) --------------------------------
// Backend nulls phone_number/email if the target user has hidden them, so
// we just check truthiness in the UI.

export interface MemberProfile {
  id: string;
  fullName: string;
  nickname: string;
  phoneNumber: string;
  email: string;
  bio: string;
  pronouns: string;
  birthday: Birthday | null;
  veganniversary: Veganniversary | null;
  profilePhotoUrl: string;
  loginLinkRequested: boolean;
}

interface WireMemberProfile {
  id: string;
  full_name: string;
  nickname?: string;
  phone_number: string;
  email: string;
  bio: string;
  pronouns: string;
  birthday?: Birthday | null;
  veganniversary?: Veganniversary | null;
  profile_photo_url: string;
  login_link_requested: boolean;
}

function fromWireProfile(w: WireMemberProfile): MemberProfile {
  return {
    id: w.id,
    fullName: w.full_name,
    nickname: w.nickname ?? '',
    phoneNumber: w.phone_number,
    email: w.email,
    bio: w.bio,
    pronouns: w.pronouns,
    birthday: w.birthday ?? null,
    veganniversary: w.veganniversary ?? null,
    profilePhotoUrl: w.profile_photo_url,
    loginLinkRequested: w.login_link_requested,
  };
}

// --- Member directory (any authed user) -------------------------------------
// Authed-only list with phone/email pre-redacted per target's privacy flags.

export interface DirectoryMember {
  id: string;
  fullName: string;
  phoneNumber: string;
  email: string;
  profilePhotoUrl: string;
}

interface WireDirectoryMember {
  id: string;
  full_name: string;
  phone_number: string;
  email: string;
  profile_photo_url: string;
}

export function useMembersDirectory() {
  return useQuery({
    queryKey: ['members-directory'] as const,
    queryFn: async () => {
      const { data } = await apiClient.get<WireDirectoryMember[]>('/api/auth/users/directory/');
      return data.map<DirectoryMember>((w) => ({
        id: w.id,
        fullName: w.full_name,
        phoneNumber: w.phone_number,
        email: w.email,
        profilePhotoUrl: w.profile_photo_url,
      }));
    },
  });
}

export function useMemberProfile(userId: string | undefined) {
  return useQuery({
    queryKey: ['member-profile', userId] as const,
    queryFn: async () => {
      const { data } = await apiClient.get<WireMemberProfile>(
        `/api/auth/users/${userId ?? ''}/profile/`,
      );
      return fromWireProfile(data);
    },
    enabled: Boolean(userId),
  });
}
