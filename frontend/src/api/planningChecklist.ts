import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import { usePlanningMutation } from './planning';
import type { components } from './types.gen';

export type ChecklistItem = components['schemas']['ChecklistItemOut'];
type ChecklistInput = components['schemas']['ChecklistItemIn'];
type MoveDirection = components['schemas']['ChecklistMoveIn']['direction'];

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

export function useUpdateChecklistItem() {
  return usePlanningMutation(async ({ id, input }: { id: string; input: ChecklistInput }) => {
    const body: components['schemas']['ChecklistItemPatchIn'] = input;
    await apiClient.patch(`${URL}${id}/`, body);
  });
}

export function useDeleteChecklistItem() {
  return usePlanningMutation(async (id: string) => {
    await apiClient.delete(`${URL}${id}/`);
  });
}

export function useMoveChecklistItem() {
  return usePlanningMutation(
    async ({ id, direction }: { id: string; direction: MoveDirection }) => {
      const body: components['schemas']['ChecklistMoveIn'] = { direction };
      await apiClient.post(`${URL}${id}/move/`, body);
    },
  );
}

export function useTickChecklistItem(slotId: string) {
  return usePlanningMutation(async ({ itemId, done }: { itemId: string; done: boolean }) => {
    const body: components['schemas']['ChecklistTickIn'] = { done };
    await apiClient.put(`/api/community/planning/slots/${slotId}/checklist/${itemId}/`, body);
  });
}
