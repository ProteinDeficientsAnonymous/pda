import { useQuery } from '@tanstack/react-query';

import type { EventRsvpQuestion } from '@/models/event';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireDefaults = components['schemas']['OfficialEventDefaultsOut'];

export type OfficialRsvpQuestion = Omit<EventRsvpQuestion, 'id'>;

export interface OfficialEventDefaults {
  cashappLink: string;
  rsvpQuestions: OfficialRsvpQuestion[];
}

export const officialEventDefaultsKeys = {
  all: ['official-event-defaults'] as const,
};

export async function fetchOfficialEventDefaults(): Promise<OfficialEventDefaults> {
  const { data } = await apiClient.get<WireDefaults>('/api/community/official-event-defaults/');
  return {
    cashappLink: data.cashapp_link,
    rsvpQuestions: data.rsvp_questions.map((q) => ({
      label: q.label,
      fieldType: q.field_type,
      options: q.options,
      required: q.required,
    })),
  };
}

export function useOfficialEventDefaults(enabled: boolean) {
  return useQuery({
    queryKey: officialEventDefaultsKeys.all,
    queryFn: fetchOfficialEventDefaults,
    staleTime: Infinity,
    enabled,
  });
}
