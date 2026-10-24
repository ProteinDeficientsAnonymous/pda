import { useMutation, useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireConnectRequest = components['schemas']['ConnectRequestOut'];
type WireConnectRedirect = components['schemas']['ConnectRedirectOut'];

export interface ConnectRequest {
  clientName: string;
  redirectHost: string;
  expiresAt: Date;
}

export const connectKeys = {
  request: (requestId: string) => ['connect', 'request', requestId] as const,
};

export function useConnectRequest(requestId: string | null) {
  return useQuery({
    queryKey: connectKeys.request(requestId ?? ''),
    enabled: Boolean(requestId),
    retry: false,
    queryFn: async (): Promise<ConnectRequest> => {
      const { data } = await apiClient.get<WireConnectRequest>(
        `/api/connect/requests/${requestId ?? ''}/`,
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
        `/api/connect/requests/${requestId}/${decision}/`,
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
