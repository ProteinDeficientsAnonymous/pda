import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

export type HostEventFeedback = components['schemas']['EventFeedbackHostOut'];

export function useHostEventFeedback(eventId: string | undefined) {
  const id = eventId ?? '';
  return useQuery({
    queryKey: ['event-feedback', 'host', id],
    queryFn: async () => {
      const { data } = await apiClient.get<HostEventFeedback>(
        `/api/community/events/${id}/feedback/`,
      );
      return data;
    },
    enabled: Boolean(eventId),
  });
}
