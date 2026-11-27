import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';
import type { MemberSearchResult } from './userSearch';

type WireClub = components['schemas']['ClubOut'];
type WireClubReps = components['schemas']['ClubRepsOut'];
type WireClubRep = components['schemas']['ClubRepOut'];

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

function repFromWire(r: WireClubRep): MemberSearchResult {
  return { id: r.id, fullName: r.full_name, phoneNumber: r.phone_number };
}

export function useClubReps() {
  return useQuery({
    queryKey: [...clubKeys.all, 'reps'] as const,
    queryFn: async (): Promise<Map<string, MemberSearchResult[]>> => {
      const { data } = await apiClient.get<WireClubReps[]>('/api/community/clubs/reps/');
      return new Map(data.map((c) => [c.club_id, c.reps.map(repFromWire)]));
    },
  });
}

/** `forClubId` overrides `clubId` for a club created in the same save, before the hook can re-render. */
export function useSetClubReps(clubId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      userIds,
      forClubId,
    }: {
      userIds: string[];
      forClubId?: string;
    }): Promise<MemberSearchResult[]> => {
      const { data } = await apiClient.put<WireClubReps>(
        `/api/community/clubs/${forClubId ?? clubId}/reps/`,
        { user_ids: userIds },
      );
      return data.reps.map(repFromWire);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: clubKeys.all });
    },
  });
}
