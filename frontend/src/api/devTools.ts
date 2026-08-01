import { useMutation, useQueryClient } from '@tanstack/react-query';

import { apiClient } from './client';
import { eventKeys } from './events';

export type DevEventVisibility = 'public' | 'members_only' | 'invite_only';

export interface DevTestEventOptions {
  isPast: boolean;
  isCanceled: boolean;
  isOfficial: boolean;
  isClub: boolean;
  makeMeHost: boolean;
  makeMeGuest: boolean;
  price: string;
  venmoLink: string;
  cashappLink: string;
  zelleInfo: string;
  cohostCount: number;
  invitedCohostCount: number;
  goingCount: number;
  maybeCount: number;
  cantGoCount: number;
  invitedCount: number;
  nonMemberGoingCount: number;
  rsvpEnabled: boolean;
  visibility: DevEventVisibility;
  maxAttendees: number | null;
  allowPlusOnes: boolean;
}

interface CreateDevTestEventResponse {
  id: string;
  slug: string;
}

export function useCreateDevTestEvents() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (options: DevTestEventOptions) => {
      const { data } = await apiClient.post<CreateDevTestEventResponse>(
        '/api/community/dev/test-events/',
        {
          is_past: options.isPast,
          is_canceled: options.isCanceled,
          is_official: options.isOfficial,
          is_club: options.isClub,
          make_me_host: options.makeMeHost,
          make_me_guest: options.makeMeGuest,
          price: options.price,
          venmo_link: options.venmoLink,
          cashapp_link: options.cashappLink,
          zelle_info: options.zelleInfo,
          cohost_count: options.cohostCount,
          invited_cohost_count: options.invitedCohostCount,
          going_count: options.goingCount,
          maybe_count: options.maybeCount,
          cant_go_count: options.cantGoCount,
          invited_count: options.invitedCount,
          non_member_going_count: options.nonMemberGoingCount,
          rsvp_enabled: options.rsvpEnabled,
          visibility: options.visibility,
          max_attendees: options.maxAttendees,
          allow_plus_ones: options.allowPlusOnes,
        },
      );
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: eventKeys.all });
    },
  });
}
