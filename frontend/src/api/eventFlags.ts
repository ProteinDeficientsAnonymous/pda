// Event flag moderation endpoints.
//
// Any authenticated user can flag an event (rate-limited 3/h server-side).
// Admin queue (list + decide) requires manage_events.
//
// Transitions: pending → dismissed | actioned. Cannot go back to pending.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { isAxiosError } from 'axios';
import { apiClient } from './client';

export type FlagStatus = 'pending' | 'dismissed' | 'actioned';

export type FlagEventErrorKind = 'already-flagged' | 'rate-limited' | 'unknown';

export class FlagEventError extends Error {
  readonly kind: FlagEventErrorKind;
  constructor(kind: FlagEventErrorKind, message: string) {
    super(message);
    this.name = 'FlagEventError';
    this.kind = kind;
  }
}

export interface EventFlag {
  id: string;
  eventId: string;
  eventTitle: string;
  flaggedById: string;
  flaggedByName: string;
  reason: string;
  status: FlagStatus;
  createdAt: string;
  reviewedAt: string | null;
}

interface WireFlag {
  id: string;
  event_id: string;
  event_title: string;
  flagged_by_id: string;
  flagged_by_name: string;
  reason: string;
  status: FlagStatus;
  created_at: string;
  reviewed_at: string | null;
}

function mapFlag(w: WireFlag): EventFlag {
  return {
    id: w.id,
    eventId: w.event_id,
    eventTitle: w.event_title,
    flaggedById: w.flagged_by_id,
    flaggedByName: w.flagged_by_name,
    reason: w.reason,
    status: w.status,
    createdAt: w.created_at,
    reviewedAt: w.reviewed_at,
  };
}

export function useEventFlags(status?: FlagStatus) {
  return useQuery({
    queryKey: ['event-flags', { status: status ?? 'all' }],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (status) params.status = status;
      const { data } = await apiClient.get<WireFlag[]>('/api/community/event-flags/', {
        params,
      });
      return data.map(mapFlag);
    },
  });
}

export function useFlagEvent(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { reason: string }) => {
      try {
        const { data } = await apiClient.post<WireFlag>(
          `/api/community/events/${eventId}/flag/`,
          { reason: args.reason },
        );
        return mapFlag(data);
      } catch (err) {
        if (isAxiosError(err)) {
          if (err.response?.status === 409) {
            throw new FlagEventError('already-flagged', "you've already flagged this event");
          }
          if (err.response?.status === 429) {
            throw new FlagEventError(
              'rate-limited',
              "you've flagged too many events — try again later",
            );
          }
        }
        throw new FlagEventError('unknown', "couldn't submit — try again");
      }
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['event-flags'] });
    },
  });
}

export function useDecideFlag() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: string; status: 'dismissed' | 'actioned' }) => {
      const { data } = await apiClient.patch<WireFlag>(`/api/community/event-flags/${args.id}/`, {
        status: args.status,
      });
      return mapFlag(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['event-flags'] });
    },
  });
}
