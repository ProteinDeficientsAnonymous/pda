import { useQuery } from '@tanstack/react-query';

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

export async function fetchEventTags(): Promise<EventTag[]> {
  const { data } = await apiClient.get<WireTag[]>('/api/community/event-tags/');
  return data.map((t) => ({ id: t.id, name: t.name, slug: t.slug }));
}

export function useEventTags() {
  return useQuery({
    queryKey: eventTagKeys.all,
    queryFn: fetchEventTags,
  });
}
