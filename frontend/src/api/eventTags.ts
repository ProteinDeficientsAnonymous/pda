// Event tags API — the curated, admin-managed tag set. Public endpoint, so it
// works for both authed and unauthed callers (calendar filtering + display).

import { useQuery } from '@tanstack/react-query';
import { apiClient } from './client';
import type { EventTag } from '@/models/event';

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
