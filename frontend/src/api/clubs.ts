import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

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

export interface ClubInput {
  name: string;
  requirements: string;
}

export function useCreateClub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: ClubInput): Promise<Club> => {
      const { data } = await apiClient.post<WireClub>('/api/community/clubs/', input);
      return clubFromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: clubKeys.all });
    },
  });
}

export function useUpdateClub(clubId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (input: ClubInput): Promise<Club> => {
      const { data } = await apiClient.patch<WireClub>(`/api/community/clubs/${clubId}/`, input);
      return clubFromWire(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: clubKeys.all });
    },
  });
}

export function useDeleteClub() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (clubId: string): Promise<void> => {
      await apiClient.delete(`/api/community/clubs/${clubId}/`);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: clubKeys.all });
    },
  });
}
