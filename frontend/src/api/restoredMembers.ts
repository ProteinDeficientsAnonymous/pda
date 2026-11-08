import { useQuery } from '@tanstack/react-query';

import { type AttendedEvent, mapAttendedEvent } from './attendedEvents';
import { apiClient } from './client';
import type { components } from './types.gen';

type WireRestoredMember = components['schemas']['RestoredMemberOut'];

export const ReturnKind = {
  RESTORED: 'restored',
  UNPAUSED: 'unpaused',
} as const satisfies Record<string, components['schemas']['ReturnKind']>;
export type ReturnKind = (typeof ReturnKind)[keyof typeof ReturnKind];

const toDate = (iso: string | null) => (iso ? new Date(iso) : null);

export interface RestoredMember {
  id: string;
  fullName: string;
  phoneNumber: string;
  kind: ReturnKind;
  restoredAt: Date | null;
  unpausedAt: Date | null;
  cameInPersonAt: Date | null;
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
        kind: w.kind,
        restoredAt: toDate(w.restored_at),
        unpausedAt: toDate(w.unpaused_at),
        cameInPersonAt: toDate(w.came_in_person_at),
        hasJoinedWhatsapp: w.has_joined_whatsapp,
        recentEvents: w.recent_events.map(mapAttendedEvent),
      }));
    },
  });
}
