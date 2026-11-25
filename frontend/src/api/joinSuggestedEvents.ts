import { useQuery } from '@tanstack/react-query';

import { apiClient } from './client';
import type { components } from './types.gen';

type WireSuggestedEvent = components['schemas']['SuggestedEventOut'];
type WireSuggestedEvents = components['schemas']['SuggestedEventsOut'];

export interface SuggestedEvent {
  id: string;
  slug: string;
  title: string;
  startDatetime: Date;
}

export interface SuggestedEvents {
  nextOfficialEvent: SuggestedEvent | null;
  clubEvent: SuggestedEvent | null;
}

function mapEvent(w: WireSuggestedEvent | null): SuggestedEvent | null {
  if (!w) return null;
  return { id: w.id, slug: w.slug, title: w.title, startDatetime: new Date(w.start_datetime) };
}

export function useJoinRequestSuggestedEvents(joinRequestId: string) {
  return useQuery({
    queryKey: ['join-requests', joinRequestId, 'suggested-events'],
    queryFn: async (): Promise<SuggestedEvents> => {
      const { data } = await apiClient.get<WireSuggestedEvents>(
        `/api/community/join-requests/${joinRequestId}/suggested-events/`,
      );
      return {
        nextOfficialEvent: mapEvent(data.next_official_event),
        clubEvent: mapEvent(data.club_event),
      };
    },
  });
}
