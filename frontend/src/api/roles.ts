// Role CRUD — mirrors backend/users/_roles.py. Create/update/delete are
// permission-gated (MANAGE_ROLES) at the endpoint; the list endpoint is
// JWT-auth only so any member can read roles (useful for the create-user
// role picker).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface Role {
  id: string;
  name: string;
  isDefault: boolean;
  permissions: string[];
  userCount: number;
}

interface WireRole {
  id: string;
  name: string;
  is_default: boolean;
  permissions: string[];
  user_count?: number;
}

function fromWire(w: WireRole): Role {
  return {
    id: w.id,
    name: w.name,
    isDefault: w.is_default,
    permissions: w.permissions,
    userCount: w.user_count ?? 0,
  };
}

const ROLES_KEY = ['roles'] as const;

export function useRoles() {
  return useQuery({
    queryKey: ROLES_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireRole[]>('/api/auth/roles/');
      return data.map(fromWire);
    },
  });
}

export interface CreateRoleInput {
  name: string;
  permissions: string[];
}

export function useCreateRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: CreateRoleInput): Promise<Role> => {
      const { data } = await apiClient.post<WireRole>('/api/auth/roles/', {
        name: input.name,
        permissions: input.permissions,
      });
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ROLES_KEY });
    },
  });
}

export interface UpdateRoleInput {
  name?: string;
  permissions?: string[];
}

export function useUpdateRole(roleId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: UpdateRoleInput): Promise<Role> => {
      const body: Record<string, unknown> = {};
      if (input.name !== undefined) body.name = input.name;
      if (input.permissions !== undefined) body.permissions = input.permissions;
      const { data } = await apiClient.patch<WireRole>(`/api/auth/roles/${roleId}/`, body);
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ROLES_KEY });
      void qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
}

export function useDeleteRole() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (roleId: string): Promise<void> => {
      await apiClient.delete(`/api/auth/roles/${roleId}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ROLES_KEY });
      void qc.invalidateQueries({ queryKey: ['users'] });
    },
  });
}
