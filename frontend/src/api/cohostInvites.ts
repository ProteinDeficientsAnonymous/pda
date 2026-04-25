// Co-host invite mutations: accept / decline / rescind.
//
// Each endpoint returns the updated EventOut so we can both invalidate the
// detail cache and seed it with fresh data — avoids a flicker where the banner
// disappears but the host row hasn't refetched yet.

import { useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { useAuthStore } from '@/auth/store';
import { mapEvent } from './eventMapper';
import type { WireEvent } from './eventMapper';
import { eventKeys } from './events';
import type { Event } from '@/models/event';

interface CohostInviteArgs {
  eventId: string;
  inviteId: string;
}

async function postAccept({ eventId, inviteId }: CohostInviteArgs): Promise<Event> {
  const { data } = await apiClient.post<WireEvent>(
    `/api/community/events/${eventId}/cohost-invites/${inviteId}/accept/`,
  );
  return mapEvent(data);
}

async function postDecline({ eventId, inviteId }: CohostInviteArgs): Promise<Event> {
  const { data } = await apiClient.post<WireEvent>(
    `/api/community/events/${eventId}/cohost-invites/${inviteId}/decline/`,
  );
  return mapEvent(data);
}

async function deleteRescind({ eventId, inviteId }: CohostInviteArgs): Promise<Event> {
  const { data } = await apiClient.delete<WireEvent>(
    `/api/community/events/${eventId}/cohost-invites/${inviteId}/`,
  );
  return mapEvent(data);
}

function useCohostInviteMutation(fn: (args: CohostInviteArgs) => Promise<Event>) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: fn,
    onSuccess: (event, vars) => {
      qc.setQueryData(eventKeys.detail(vars.eventId, isAuthed), event);
      void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
    },
  });
}

export function useAcceptCohostInvite() {
  return useCohostInviteMutation(postAccept);
}

export function useDeclineCohostInvite() {
  return useCohostInviteMutation(postDecline);
}

export function useRescindCohostInvite() {
  return useCohostInviteMutation(deleteRescind);
}
