import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { FeatureFlagKey } from '@/models/featureFlags';

import { apiClient } from './client';

interface WireFlags {
  flags: Record<string, boolean>;
}

const FLAGS_KEY = ['feature-flags'] as const;

// Flags change rarely; avoid refetching on every mount/focus.
const FLAGS_STALE_TIME = 5 * 60 * 1000;

export function useFeatureFlags() {
  return useQuery({
    queryKey: FLAGS_KEY,
    queryFn: async () => {
      const { data } = await apiClient.get<WireFlags>('/api/community/feature-flags/');
      return data.flags;
    },
    staleTime: FLAGS_STALE_TIME,
  });
}

export function useFlag(key: FeatureFlagKey): boolean {
  const { data } = useFeatureFlags();
  return data?.[key] ?? false;
}

export interface SetFeatureFlagInput {
  key: FeatureFlagKey;
  enabled: boolean;
}

export function useSetFeatureFlag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ key, enabled }: SetFeatureFlagInput) => {
      const { data } = await apiClient.patch<WireFlags>(`/api/community/feature-flags/${key}/`, {
        enabled,
      });
      return data.flags;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: FLAGS_KEY });
    },
  });
}
