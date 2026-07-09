import { useMutation } from '@tanstack/react-query';

import { reportError } from '@/utils/errorReporter';

import { apiClient } from './client';
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
