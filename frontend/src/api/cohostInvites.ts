import { useMutation, useQueryClient } from '@tanstack/react-query';

import { useAuthStore } from '@/auth/store';
import type { Event } from '@/models/event';

import { apiClient } from './client';
import type { WireEvent } from './eventMapper';
import { mapEvent } from './eventMapper';
import { eventKeys, setEventDetailData } from './events';

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

async function deleteCohost({
  eventId,
  userId,
}: {
  eventId: string;
  userId: string;
}): Promise<Event> {
  const { data } = await apiClient.delete<WireEvent>(
    `/api/community/events/${eventId}/cohosts/${userId}/`,
  );
  return mapEvent(data);
}

async function postAddCohosts({
  eventId,
  userIds,
}: {
  eventId: string;
  userIds: string[];
}): Promise<Event> {
  const { data } = await apiClient.post<WireEvent>(
    `/api/community/events/${eventId}/cohost-invites/`,
    { user_ids: userIds },
  );
  return mapEvent(data);
}

function useCohostInviteMutation<TArgs extends { eventId: string }>(
  fn: (args: TArgs) => Promise<Event>,
) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: fn,
    onSuccess: (event) => {
      setEventDetailData(qc, event, isAuthed);
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

export function useRemoveCohost() {
  return useCohostInviteMutation(deleteCohost);
}

export function useAddCohosts() {
  return useCohostInviteMutation(postAddCohosts);
}
