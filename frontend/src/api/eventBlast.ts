// Host email-blast mutation — email everyone who RSVP'd to an event.
//
// Backend: POST /api/community/events/{id}/email-blast/ (host/co-host only,
// rate-limited 5/h per host+event). See backend community/_event_blasts.py.

import { useMutation } from '@tanstack/react-query';
import { apiClient } from './client';
import { reportError } from '@/utils/errorReporter';
import type { components } from './types.gen';

export type EmailBlastIn = components['schemas']['EmailBlastIn'];
export type EmailBlastResult = components['schemas']['EmailBlastOut'];

const ROUTE = '/events';

export function useEmailBlast(eventId: string) {
  return useMutation({
    mutationFn: async (payload: EmailBlastIn): Promise<EmailBlastResult> => {
      const { data } = await apiClient.post<EmailBlastResult>(
        `/api/community/events/${eventId}/email-blast/`,
        payload,
      );
      return data;
    },
    onError: (err) => {
      void reportError(err, ROUTE, { action: 'email-blast', eventId });
    },
  });
}
