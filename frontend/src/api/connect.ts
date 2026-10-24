import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireConnectRequest = components['schemas']['ConnectRequestOut'];
type WireConnectRedirect = components['schemas']['ConnectRedirectOut'];
type WireConnectedApp = components['schemas']['ConnectedAppOut'];

export interface ConnectRequest {
  clientName: string;
  redirectHost: string;
  expiresAt: Date;
}

export interface ConnectedApp {
  id: string;
  clientName: string;
  createdAt: Date;
  lastUsedAt: Date | null;
}

// encodeURIComponent leaves '.' alone, so a bare '..' id would still traverse
function seg(id: string): string {
  return encodeURIComponent(id).replaceAll('.', '%2E');
}

export const connectKeys = {
  request: (requestId: string) => ['connect', 'request', requestId] as const,
  apps: ['connect', 'apps'] as const,
  memberApps: (userId: string) => ['connect', 'member-apps', userId] as const,
};

function mapApp(a: WireConnectedApp): ConnectedApp {
  return {
    id: a.id,
    clientName: a.client_name,
    createdAt: new Date(a.created_at),
    lastUsedAt: a.last_used_at ? new Date(a.last_used_at) : null,
  };
}

export function useConnectRequest(requestId: string | null) {
  return useQuery({
    queryKey: connectKeys.request(requestId ?? ''),
    enabled: Boolean(requestId),
    retry: false,
    queryFn: async (): Promise<ConnectRequest> => {
      const { data } = await apiClient.get<WireConnectRequest>(
        `/api/connect/requests/${seg(requestId ?? '')}/`,
      );
      return {
        clientName: data.client_name,
        redirectHost: data.redirect_host,
        expiresAt: new Date(data.expires_at),
      };
    },
  });
}

function useConnectDecision(decision: 'approve' | 'deny') {
  return useMutation({
    mutationFn: async (requestId: string): Promise<string> => {
      const { data } = await apiClient.post<WireConnectRedirect>(
        `/api/connect/requests/${seg(requestId)}/${decision}/`,
      );
      return data.redirect_url;
    },
  });
}

export function useApproveConnect() {
  return useConnectDecision('approve');
}

export function useDenyConnect() {
  return useConnectDecision('deny');
}

export function useConnectedApps() {
  return useQuery({
    queryKey: connectKeys.apps,
    queryFn: async (): Promise<ConnectedApp[]> => {
      const { data } = await apiClient.get<WireConnectedApp[]>('/api/connect/apps/');
      return data.map(mapApp);
    },
  });
}

export function useRevokeConnectedApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (grantId: string) => {
      await apiClient.delete(`/api/connect/apps/${seg(grantId)}/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: connectKeys.apps }),
  });
}

export function useMemberConnectedApps(userId: string) {
  return useQuery({
    queryKey: connectKeys.memberApps(userId),
    queryFn: async (): Promise<ConnectedApp[]> => {
      const { data } = await apiClient.get<WireConnectedApp[]>(
        `/api/connect/users/${seg(userId)}/apps/`,
      );
      return data.map(mapApp);
    },
  });
}

export function useRevokeMemberConnectedApp(userId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (grantId: string) => {
      await apiClient.delete(`/api/connect/users/${seg(userId)}/apps/${seg(grantId)}/`);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: connectKeys.memberApps(userId) }),
  });
}
