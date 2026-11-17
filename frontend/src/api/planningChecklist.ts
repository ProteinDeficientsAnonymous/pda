import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

export type ChecklistItem = components['schemas']['ChecklistItemOut'];

export const PLANNING_GUIDELINES_SLUG = 'planning-guidelines';

export function useChecklist() {
  return useQuery({
    queryKey: ['planning', 'checklist'],
    queryFn: async () => {
      const { data } = await apiClient.get<ChecklistItem[]>('/api/community/planning/checklist/');
      return data;
    },
  });
}
