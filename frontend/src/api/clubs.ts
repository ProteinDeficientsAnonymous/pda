import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireClub = components['schemas']['ClubOut'];

export interface Club {
  id: string;
  name: string;
  requirements: string;
}

export const clubKeys = {
  all: ['clubs'] as const,
};

export function clubFromWire(c: WireClub): Club {
  return { id: c.id, name: c.name, requirements: c.requirements };
}

export function useClubs() {
  return useQuery({
    queryKey: clubKeys.all,
    queryFn: async (): Promise<Club[]> => {
      const { data } = await apiClient.get<WireClub[]>('/api/community/clubs/');
      return data.map(clubFromWire);
    },
  });
}
