// DateTime poll API — create, get, vote, finalize, delete, option CRUD.
// Mirrors backend/community/_polls.py. GET is optional-auth, so unauthed
// viewers see counts but not their own votes.

import { isAxiosError } from 'axios';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { eventKeys } from './events';
import { mapEventPoll, type WireEventPoll } from './eventPollMapper';
import { useAuthStore } from '@/auth/store';
import { VoteChoice, type EventPoll } from '@/models/eventPoll';

export const eventPollKeys = {
  all: ['event-poll'] as const,
  detail: (eventId: string, isAuthed: boolean) =>
    ['event-poll', eventId, { authed: isAuthed }] as const,
};

function pollUrl(eventId: string, suffix = ''): string {
  return `/api/community/events/${eventId}/poll/${suffix}`;
}

async function fetchEventPoll(eventId: string): Promise<EventPoll | null> {
  try {
    const { data } = await apiClient.get<WireEventPoll>(pollUrl(eventId));
    return mapEventPoll(data);
  } catch (err) {
    if (isAxiosError(err) && err.response?.status === 404) return null;
    throw err;
  }
}

export function useEventPoll(eventId: string, hasPoll: boolean) {
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useQuery({
    queryKey: eventPollKeys.detail(eventId, isAuthed),
    queryFn: () => fetchEventPoll(eventId),
    enabled: Boolean(eventId) && hasPoll,
  });
}

function extractPollError(err: unknown): string {
  if (isAxiosError(err)) {
    if (err.response?.status === 429) return 'slow down — try again in a moment';
    const data = err.response?.data as { detail?: unknown } | undefined;
    if (typeof data?.detail === 'string') return data.detail;
  }
  return "couldn't update the poll — try again";
}

function invalidateEventAndPoll(
  qc: ReturnType<typeof useQueryClient>,
  eventId: string,
  isAuthed: boolean,
  poll: EventPoll | null,
) {
  if (poll) qc.setQueryData(eventPollKeys.detail(eventId, isAuthed), poll);
  else qc.removeQueries({ queryKey: eventPollKeys.detail(eventId, isAuthed) });
  // Finalize + create + delete all change event.hasPoll / event.startDatetime.
  void qc.invalidateQueries({ queryKey: eventKeys.detail(eventId, isAuthed) });
  void qc.invalidateQueries({ queryKey: eventKeys.list(isAuthed) });
}

export function useCreatePoll(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (options: Date[]): Promise<EventPoll> => {
      const { data } = await apiClient.post<WireEventPoll>(pollUrl(eventId), {
        options: options.map((d) => d.toISOString()),
      });
      return mapEventPoll(data);
    },
    onSuccess: (poll) => {
      invalidateEventAndPoll(qc, eventId, isAuthed, poll);
    },
  });
}

export function useDeletePoll(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (): Promise<void> => {
      await apiClient.delete(pollUrl(eventId));
    },
    onSuccess: () => {
      invalidateEventAndPoll(qc, eventId, isAuthed, null);
    },
  });
}

export function useFinalizePoll(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (winningOptionId: string): Promise<EventPoll> => {
      const { data } = await apiClient.post<WireEventPoll>(pollUrl(eventId, 'finalize/'), {
        winning_option_id: winningOptionId,
      });
      return mapEventPoll(data);
    },
    onSuccess: (poll) => {
      invalidateEventAndPoll(qc, eventId, isAuthed, poll);
    },
  });
}

export function useAddPollOption(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (datetime: Date): Promise<EventPoll> => {
      const { data } = await apiClient.post<WireEventPoll>(pollUrl(eventId, 'options/'), {
        datetime: datetime.toISOString(),
      });
      return mapEventPoll(data);
    },
    onSuccess: (poll) => {
      qc.setQueryData(eventPollKeys.detail(eventId, isAuthed), poll);
    },
  });
}

export function useUpdatePollOption(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (args: { optionId: string; datetime: Date }): Promise<EventPoll> => {
      const { data } = await apiClient.patch<WireEventPoll>(
        pollUrl(eventId, `options/${args.optionId}/`),
        { datetime: args.datetime.toISOString() },
      );
      return mapEventPoll(data);
    },
    onSuccess: (poll) => {
      qc.setQueryData(eventPollKeys.detail(eventId, isAuthed), poll);
    },
  });
}

export function useDeletePollOption(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (optionId: string): Promise<EventPoll> => {
      const { data } = await apiClient.delete<WireEventPoll>(
        pollUrl(eventId, `options/${optionId}/`),
      );
      return mapEventPoll(data);
    },
    onSuccess: (poll) => {
      qc.setQueryData(eventPollKeys.detail(eventId, isAuthed), poll);
    },
  });
}

// Optimistic vote. Backend expects the full merged { optionId -> choice } map.
// We shift counts + voter lists locally so the strip updates instantly.
export function useVotePoll(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async (votes: Record<string, VoteChoice>): Promise<EventPoll> => {
      const { data } = await apiClient.post<WireEventPoll>(pollUrl(eventId, 'vote/'), { votes });
      return mapEventPoll(data);
    },
    onMutate: async (votes) => {
      const key = eventPollKeys.detail(eventId, isAuthed);
      await qc.cancelQueries({ queryKey: key });
      const prev = qc.getQueryData<EventPoll>(key);
      if (prev) {
        const user = useAuthStore.getState().user;
        qc.setQueryData<EventPoll>(key, applyOptimisticVotes(prev, votes, user));
      }
      return { prev };
    },
    onError: (_err, _votes, ctx) => {
      const prev = (ctx as { prev?: EventPoll } | undefined)?.prev;
      if (prev) qc.setQueryData(eventPollKeys.detail(eventId, isAuthed), prev);
    },
    onSuccess: (poll) => {
      qc.setQueryData(eventPollKeys.detail(eventId, isAuthed), poll);
    },
  });
}

function applyOptimisticVotes(
  poll: EventPoll,
  nextVotes: Record<string, VoteChoice>,
  user: { id: string; displayName: string; profilePhotoUrl?: string | null } | null,
): EventPoll {
  const voter = user
    ? { userId: user.id, name: user.displayName, photoUrl: user.profilePhotoUrl ?? '' }
    : null;
  const options = poll.options.map((opt) => {
    const prev = poll.myVotes[opt.id];
    const next = nextVotes[opt.id];
    if (prev === next) return opt;
    return applyVoteShift(opt, prev, next, voter);
  });
  return { ...poll, options, myVotes: nextVotes };
}

function applyVoteShift(
  opt: EventPollOptionLike,
  prev: VoteChoice | undefined,
  next: VoteChoice | undefined,
  voter: { userId: string; name: string; photoUrl: string } | null,
): EventPollOptionLike {
  const updated = { ...opt };
  if (prev) {
    updated[countField(prev)] = Math.max(0, updated[countField(prev)] - 1);
    updated[voterField(prev)] = updated[voterField(prev)].filter((v) => v.userId !== voter?.userId);
  }
  if (next && voter) {
    updated[countField(next)] = updated[countField(next)] + 1;
    updated[voterField(next)] = [...updated[voterField(next)], voter];
  }
  return updated;
}

type EventPollOptionLike = EventPoll['options'][number] & {
  yesCount: number;
  maybeCount: number;
  noCount: number;
  yesVoters: readonly { userId: string; name: string; photoUrl: string }[];
  maybeVoters: readonly { userId: string; name: string; photoUrl: string }[];
  noVoters: readonly { userId: string; name: string; photoUrl: string }[];
};

function countField(c: VoteChoice): 'yesCount' | 'maybeCount' | 'noCount' {
  if (c === VoteChoice.Yes) return 'yesCount';
  if (c === VoteChoice.Maybe) return 'maybeCount';
  return 'noCount';
}

function voterField(c: VoteChoice): 'yesVoters' | 'maybeVoters' | 'noVoters' {
  if (c === VoteChoice.Yes) return 'yesVoters';
  if (c === VoteChoice.Maybe) return 'maybeVoters';
  return 'noVoters';
}

export { extractPollError };
