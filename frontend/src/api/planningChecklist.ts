import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import { usePlanningMutation } from './planning';
import type { components } from './types.gen';

export type ChecklistItem = components['schemas']['ChecklistItemOut'];
type ChecklistInput = components['schemas']['ChecklistItemIn'];

const URL = '/api/community/planning/checklist/';
const CHECKLIST_KEY = ['planning', 'checklist'];

export const PLANNING_GUIDELINES_SLUG = 'planning-guidelines';

export function useChecklist() {
  return useQuery({
    queryKey: CHECKLIST_KEY,
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

export function useReorderChecklist() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (ids: string[]) => {
      const body: components['schemas']['ChecklistOrderIn'] = { ids };
      await apiClient.put(`${URL}order/`, body);
    },
    onMutate: async (ids) => {
      await qc.cancelQueries({ queryKey: CHECKLIST_KEY });
      qc.setQueryData<ChecklistItem[]>(CHECKLIST_KEY, (items) => {
        if (!items) return items;
        const byId = new Map(items.map((i) => [i.id, i]));
        return ids.flatMap((id) => byId.get(id) ?? []);
      });
    },
    onSettled: () => qc.invalidateQueries({ queryKey: ['planning'] }),
  });
}

export function useTickChecklistItem(slotId: string) {
  return usePlanningMutation(async ({ itemId, done }: { itemId: string; done: boolean }) => {
    const body: components['schemas']['ChecklistTickIn'] = { done };
    await apiClient.put(`/api/community/planning/slots/${slotId}/checklist/${itemId}/`, body);
  });
}
