import { useQuery } from '@tanstack/react-query';

import { type AttendedEvent, mapAttendedEvent } from './attendedEvents';
import { apiClient } from './client';
import type { components } from './types.gen';

type WireRestoredMember = components['schemas']['RestoredMemberOut'];

export interface RestoredMember {
  id: string;
  fullName: string;
  phoneNumber: string;
  restoredAt: Date;
  hasJoinedWhatsapp: boolean;
  recentEvents: AttendedEvent[];
}

// Nested under join-requests so the whatsapp toggle's invalidation refreshes it too.
export function useRestoredMembers() {
  return useQuery({
    queryKey: ['join-requests', 'restored'],
    queryFn: async () => {
      const { data } = await apiClient.get<WireRestoredMember[]>('/api/auth/users/restored/');
      return data.map((w): RestoredMember => ({
        id: w.id,
        fullName: w.full_name,
        phoneNumber: w.phone_number,
        restoredAt: new Date(w.restored_at),
        hasJoinedWhatsapp: w.has_joined_whatsapp,
        recentEvents: w.recent_events.map(mapAttendedEvent),
      }));
    },
  });
}
