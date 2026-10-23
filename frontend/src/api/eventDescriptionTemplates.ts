import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireTemplates = components['schemas']['EventDescriptionTemplatesOut'];

export interface EventDescriptionTemplates {
  officialWalk: string;
  officialNonWalk: string;
}

export async function fetchEventDescriptionTemplates(): Promise<EventDescriptionTemplates> {
  const { data } = await apiClient.get<WireTemplates>(
    '/api/community/event-description-templates/',
  );
  return { officialWalk: data.official_walk, officialNonWalk: data.official_non_walk };
}

export function useEventDescriptionTemplates() {
  return useQuery({
    queryKey: ['event-description-templates'],
    queryFn: fetchEventDescriptionTemplates,
    staleTime: Infinity,
  });
}
