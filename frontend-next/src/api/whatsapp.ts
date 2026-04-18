// WhatsApp bot config + connection status. Secret is never returned — we
// track `hasSecret` instead, and sending a value in the PATCH rotates it.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';

export interface WhatsappConfig {
  botUrl: string;
  groupId: string;
  hasSecret: boolean;
}

interface WireConfig {
  bot_url: string;
  group_id: string;
  has_secret: boolean;
}

export function useWhatsappConfig() {
  return useQuery({
    queryKey: ['whatsapp', 'config'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireConfig>('/api/community/whatsapp/config/');
      return { botUrl: data.bot_url, groupId: data.group_id, hasSecret: data.has_secret };
    },
  });
}

export interface WhatsappConfigUpdate {
  botUrl?: string;
  botSecret?: string;
  groupId?: string;
}

export function useUpdateWhatsappConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: WhatsappConfigUpdate) => {
      const body: Record<string, string> = {};
      if (patch.botUrl !== undefined) body.bot_url = patch.botUrl;
      if (patch.botSecret !== undefined) body.bot_secret = patch.botSecret;
      if (patch.groupId !== undefined) body.group_id = patch.groupId;
      const { data } = await apiClient.patch<WireConfig>('/api/community/whatsapp/config/', body);
      return { botUrl: data.bot_url, groupId: data.group_id, hasSecret: data.has_secret };
    },
    onSuccess: (config) => {
      qc.setQueryData(['whatsapp', 'config'], config);
      void qc.invalidateQueries({ queryKey: ['whatsapp', 'status'] });
    },
  });
}

export function useWhatsappStatus() {
  // Server-side endpoint calls the bot's /status; a 5s timeout returns
  // connected:false. Refetch every 30s so admins see drift.
  return useQuery({
    queryKey: ['whatsapp', 'status'],
    queryFn: async () => {
      const { data } = await apiClient.get<{ connected: boolean }>(
        '/api/community/whatsapp/status/',
      );
      return data.connected;
    },
    refetchInterval: 30_000,
    refetchIntervalInBackground: false,
  });
}
