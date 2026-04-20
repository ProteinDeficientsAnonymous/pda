// Admin user management — list, create, edit, magic-link resend, role patch.
// Mirrors backend/users/_management.py.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

// --- Domain types (camelCase) ------------------------------------------------

export interface MemberRole {
  id: string;
  name: string;
  isDefault: boolean;
  permissions: string[];
}

export interface Member {
  id: string;
  displayName: string;
  phoneNumber: string;
  email: string;
  bio: string;
  profilePhotoUrl: string;
  showPhone: boolean;
  showEmail: boolean;
  isSuperuser: boolean;
  isPaused: boolean;
  needsOnboarding: boolean;
  loginLinkRequested: boolean;
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
  display_name: string;
  phone_number: string;
  email?: string;
  bio?: string;
  profile_photo_url?: string;
  show_phone?: boolean;
  show_email?: boolean;
  is_superuser?: boolean;
  is_paused?: boolean;
  needs_onboarding?: boolean;
  login_link_requested?: boolean;
  roles: WireRole[];
}

function mapRole(r: WireRole): MemberRole {
  return {
    id: r.id,
    name: r.name,
    isDefault: r.is_default,
    permissions: r.permissions,
  };
}

function fromWire(w: WireMember): Member {
  return {
    id: w.id,
    displayName: w.display_name,
    phoneNumber: w.phone_number,
    email: w.email ?? '',
    bio: w.bio ?? '',
    profilePhotoUrl: w.profile_photo_url ?? '',
    showPhone: w.show_phone ?? true,
    showEmail: w.show_email ?? true,
    isSuperuser: w.is_superuser ?? false,
    isPaused: w.is_paused ?? false,
    needsOnboarding: w.needs_onboarding ?? false,
    loginLinkRequested: w.login_link_requested ?? false,
    roles: w.roles.map(mapRole),
  };
}

// --- Queries / mutations -----------------------------------------------------

const USERS_KEY = ['users'] as const;

export function useUsers() {
  return useQuery({
    queryKey: USERS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireMember[]>('/api/auth/users/');
      return data.map(fromWire);
    },
  });
}

export interface CreateUserInput {
  phoneNumber: string;
  displayName?: string;
  email?: string;
  roleId?: string;
}

export interface CreateUserResult {
  id: string;
  phoneNumber: string;
  displayName: string;
  magicLinkToken: string;
}

interface WireCreateResult {
  id: string;
  phone_number: string;
  display_name: string;
  magic_link_token: string;
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateUserInput): Promise<CreateUserResult> => {
      const body: Record<string, unknown> = { phone_number: input.phoneNumber };
      if (input.displayName !== undefined) body.display_name = input.displayName;
      if (input.email !== undefined) body.email = input.email;
      if (input.roleId !== undefined) body.role_id = input.roleId;
      const { data } = await apiClient.post<WireCreateResult>('/api/auth/create-user/', body);
      return {
        id: data.id,
        phoneNumber: data.phone_number,
        displayName: data.display_name,
        magicLinkToken: data.magic_link_token,
      };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export interface UpdateUserInput {
  phoneNumber?: string;
  displayName?: string;
  email?: string;
  isPaused?: boolean;
}

export function useUpdateUser(userId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: UpdateUserInput): Promise<Member> => {
      const body: Record<string, unknown> = {};
      if (input.phoneNumber !== undefined) body.phone_number = input.phoneNumber;
      if (input.displayName !== undefined) body.display_name = input.displayName;
      if (input.email !== undefined) body.email = input.email;
      if (input.isPaused !== undefined) body.is_paused = input.isPaused;
      const { data } = await apiClient.patch<WireMember>(`/api/auth/users/${userId}/`, body);
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
    },
  });
}

export interface BulkCreateResult {
  row: number;
  phoneNumber: string;
  success: boolean;
  error?: string;
  magicLinkToken?: string;
}

export interface BulkCreateResponse {
  results: BulkCreateResult[];
  created: number;
  failed: number;
}

interface WireBulkResult {
  row: number;
  phone_number: string;
  success: boolean;
  error?: string;
  magic_link_token?: string;
}

interface WireBulkResponse {
  results: WireBulkResult[];
  created: number;
  failed: number;
}

export function useBulkCreateUsers() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (phoneNumbers: string[]): Promise<BulkCreateResponse> => {
      const { data } = await apiClient.post<WireBulkResponse>('/api/auth/bulk-create-users/', {
        phone_numbers: phoneNumbers,
      });
      return {
        created: data.created,
        failed: data.failed,
        results: data.results.map((r) => {
          const result: BulkCreateResult = {
            row: r.row,
            phoneNumber: r.phone_number,
            success: r.success,
          };
          if (r.error !== undefined) result.error = r.error;
          if (r.magic_link_token !== undefined) result.magicLinkToken = r.magic_link_token;
          return result;
        }),
      };
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: USERS_KEY });
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
  displayName: string;
  phoneNumber: string;
  email: string;
  bio: string;
  profilePhotoUrl: string;
  loginLinkRequested: boolean;
}

interface WireMemberProfile {
  id: string;
  display_name: string;
  phone_number: string;
  email: string;
  bio: string;
  profile_photo_url: string;
  login_link_requested: boolean;
}

function fromWireProfile(w: WireMemberProfile): MemberProfile {
  return {
    id: w.id,
    displayName: w.display_name,
    phoneNumber: w.phone_number,
    email: w.email,
    bio: w.bio,
    profilePhotoUrl: w.profile_photo_url,
    loginLinkRequested: w.login_link_requested,
  };
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
