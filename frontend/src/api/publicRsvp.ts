import { useMutation } from '@tanstack/react-query';

import type { components } from '@/api/types.gen';

import { apiClient } from './client';

export type PublicRsvpIn = components['schemas']['PublicRsvpIn'];
export type PublicRsvpOut = components['schemas']['PublicRsvpOut'];

interface SubmitArgs {
  eventId: string;
  payload: PublicRsvpIn;
}

export function useSubmitPublicRsvp() {
  return useMutation({
    mutationFn: async ({ eventId, payload }: SubmitArgs) => {
      const { data } = await apiClient.post<PublicRsvpOut>(
        `/api/community/public/events/${eventId}/rsvp/`,
        payload,
      );
      return data;
    },
  });
}
