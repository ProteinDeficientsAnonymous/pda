import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';

export interface SpeechTemplate {
  sharedPm: string;
  walkPm: string;
  restaurantPm: string;
  openRoles: string[];
  updatedAt: string;
}

export interface SpeechTemplateUpdate {
  sharedPm?: string;
  walkPm?: string;
  restaurantPm?: string;
  openRoles?: string[];
}

interface WireSpeechTemplate {
  shared_pm: string;
  walk_pm: string;
  restaurant_pm: string;
  open_roles: string[];
  updated_at: string;
}

const TEMPLATE_KEY = ['speech-template'] as const;
const TEMPLATE_URL = '/api/community/speech-template/';

function mapTemplate(data: WireSpeechTemplate): SpeechTemplate {
  return {
    sharedPm: data.shared_pm,
    walkPm: data.walk_pm,
    restaurantPm: data.restaurant_pm,
    openRoles: data.open_roles,
    updatedAt: data.updated_at,
  };
}

export function useSpeechTemplate() {
  return useQuery({
    queryKey: TEMPLATE_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireSpeechTemplate>(TEMPLATE_URL);
      return mapTemplate(data);
    },
  });
}

export function useUpdateSpeechTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (patch: SpeechTemplateUpdate) => {
      const body: Record<string, string | string[]> = {};
      if (patch.sharedPm !== undefined) body.shared_pm = patch.sharedPm;
      if (patch.walkPm !== undefined) body.walk_pm = patch.walkPm;
      if (patch.restaurantPm !== undefined) body.restaurant_pm = patch.restaurantPm;
      if (patch.openRoles !== undefined) body.open_roles = patch.openRoles;
      const { data } = await apiClient.patch<WireSpeechTemplate>(TEMPLATE_URL, body);
      return mapTemplate(data);
    },
    onSuccess: (template) => {
      qc.setQueryData(TEMPLATE_KEY, template);
    },
  });
}
