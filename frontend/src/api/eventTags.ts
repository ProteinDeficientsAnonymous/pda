import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import type { EventTag } from '@/models/event';

import { apiClient } from './client';

interface WireTag {
  id: string;
  name: string;
  slug: string;
}

export const eventTagKeys = {
  all: ['event-tags'] as const,
};

function fromWire(t: WireTag): EventTag {
  return { id: t.id, name: t.name, slug: t.slug };
}

export async function fetchEventTags(): Promise<EventTag[]> {
  const { data } = await apiClient.get<WireTag[]>('/api/community/event-tags/');
  return data.map(fromWire);
}

export function useEventTags() {
  return useQuery({
    queryKey: eventTagKeys.all,
    queryFn: fetchEventTags,
  });
}

export function useCreateEventTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (name: string): Promise<EventTag> => {
      const { data } = await apiClient.post<WireTag>('/api/community/event-tags/', { name });
      return fromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: eventTagKeys.all });
    },
  });
}

export function useDeleteEventTag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (tagId: string): Promise<void> => {
      await apiClient.delete(`/api/community/event-tags/${tagId}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: eventTagKeys.all });
    },
  });
}
