import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import { usePlanningMutation } from './planning';
import type { components } from './types.gen';

export type ChecklistItem = components['schemas']['ChecklistItemOut'];
type ChecklistInput = components['schemas']['ChecklistItemIn'];

const URL = '/api/community/planning/checklist/';

export const PLANNING_GUIDELINES_SLUG = 'planning-guidelines';

export function useChecklist() {
  return useQuery({
    queryKey: ['planning', 'checklist'],
    queryFn: async () => {
      const { data } = await apiClient.get<ChecklistItem[]>(URL);
      return data;
    },
  });
}

export function useCreateChecklistItem() {
  return usePlanningMutation(async (input: ChecklistInput) => {
    await apiClient.post(URL, input);
  });
}
