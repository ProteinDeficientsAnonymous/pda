import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';

import { apiClient } from './client';
import type { WireEvent } from './eventMapper';
import { mapEvent } from './eventMapper';
import { eventKeys } from './events';

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
