// Comments API — list + post + reply + delete + react. Mirrors
// backend/community/_event_comments.py. GET is optional-auth; all writes
// require auth + an EventRSVP on the event.

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from './client';
import { eventKeys } from './events';
import { mapComment, mapCommentList, mapReply, type WireCommentList } from './eventCommentMapper';
import { useAuthStore } from '@/auth/store';
import type {
  EventComment,
  EventCommentList,
  EventCommentReply,
  ReactionEmojiValue,
} from '@/models/eventComment';

// ---------------------------------------------------------------------------
// Wire types for write responses (not exported by the mapper)
// ---------------------------------------------------------------------------

interface WireReactionSummary {
  emoji: string;
  count: number;
  reacted_by_me: boolean;
}

interface WireReplyResponse {
  id: string;
  author_id: string;
  author_display_name: string;
  author_photo_url: string;
  body: string;
  is_deleted: boolean;
  created_at: string;
  reactions: WireReactionSummary[];
  can_delete: boolean;
}

interface WireCommentResponse extends WireReplyResponse {
  replies: WireReplyResponse[];
}

// ---------------------------------------------------------------------------
// Key factory
// ---------------------------------------------------------------------------

export const eventCommentKeys = {
  all: ['event-comments'] as const,
  list: (eventId: string) => ['event-comments', eventId] as const,
};

// ---------------------------------------------------------------------------
// Fetcher
// ---------------------------------------------------------------------------

function commentsUrl(eventId: string, suffix = ''): string {
  return `/api/community/events/${eventId}/comments/${suffix}`;
}

async function fetchEventComments(eventId: string): Promise<EventCommentList> {
  const { data } = await apiClient.get<WireCommentList>(commentsUrl(eventId));
  return mapCommentList(data);
}

// ---------------------------------------------------------------------------
// Read hook
// ---------------------------------------------------------------------------

export function useEventComments(eventId: string) {
  return useQuery({
    queryKey: eventCommentKeys.list(eventId),
    queryFn: () => fetchEventComments(eventId),
    enabled: Boolean(eventId),
  });
}

// ---------------------------------------------------------------------------
// usePostComment
// ---------------------------------------------------------------------------

interface PostCommentVars {
  body: string;
}

export function usePostComment(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async ({ body }: PostCommentVars): Promise<EventComment> => {
      const { data } = await apiClient.post<WireCommentResponse>(commentsUrl(eventId), { body });
      return mapComment(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: eventCommentKeys.list(eventId) });
      void qc.invalidateQueries({ queryKey: eventKeys.detail(eventId, isAuthed) });
    },
  });
}

// ---------------------------------------------------------------------------
// usePostReply
// ---------------------------------------------------------------------------

interface PostReplyVars {
  parentId: string;
  body: string;
}

export function usePostReply(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ parentId, body }: PostReplyVars): Promise<EventCommentReply> => {
      const { data } = await apiClient.post<WireReplyResponse>(
        commentsUrl(eventId, `${parentId}/replies/`),
        { body },
      );
      return mapReply(data);
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: eventCommentKeys.list(eventId) });
    },
  });
}

// ---------------------------------------------------------------------------
// useDeleteComment — optimistic: mark deleted immediately, rollback on error
// ---------------------------------------------------------------------------

interface DeleteCommentVars {
  commentId: string;
}

export function useDeleteComment(eventId: string) {
  const qc = useQueryClient();
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  return useMutation({
    mutationFn: async ({ commentId }: DeleteCommentVars) => {
      await apiClient.delete(commentsUrl(eventId, `${commentId}/`));
    },
    onMutate: async ({ commentId }) => {
      await qc.cancelQueries({ queryKey: eventCommentKeys.list(eventId) });
      const prev = qc.getQueryData<EventCommentList>(eventCommentKeys.list(eventId));
      if (prev) {
        const next: EventCommentList = {
          ...prev,
          items: prev.items.map((c) => {
            if (c.id === commentId) {
              return { ...c, isDeleted: true, body: '', reactions: [] };
            }
            return {
              ...c,
              replies: c.replies.map((r) =>
                r.id === commentId ? { ...r, isDeleted: true, body: '', reactions: [] } : r,
              ),
            };
          }),
        };
        qc.setQueryData(eventCommentKeys.list(eventId), next);
      }
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) {
        qc.setQueryData(eventCommentKeys.list(eventId), ctx.prev);
      }
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: eventCommentKeys.list(eventId) });
      void qc.invalidateQueries({ queryKey: eventKeys.detail(eventId, isAuthed) });
    },
  });
}

// ---------------------------------------------------------------------------
// useToggleReaction — optimistic toggle on comment or reply row
// ---------------------------------------------------------------------------

interface ToggleReactionVars {
  commentId: string;
  emoji: ReactionEmojiValue;
}

function toggleOnRow<T extends EventCommentReply>(
  row: T,
  commentId: string,
  emoji: ReactionEmojiValue,
): T {
  if (row.id !== commentId) return row;
  const existing = row.reactions.find((r) => r.emoji === emoji);
  let next = row.reactions.slice();
  if (existing?.reactedByMe) {
    next = next
      .map((r) => (r.emoji === emoji ? { ...r, count: r.count - 1, reactedByMe: false } : r))
      .filter((r) => r.count > 0);
  } else if (existing) {
    next = next.map((r) =>
      r.emoji === emoji ? { ...r, count: r.count + 1, reactedByMe: true } : r,
    );
  } else {
    next = [...next, { emoji, count: 1, reactedByMe: true }];
  }
  return { ...row, reactions: next };
}

export function useToggleReaction(eventId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ commentId, emoji }: ToggleReactionVars): Promise<EventComment> => {
      const { data } = await apiClient.post<WireCommentResponse>(
        commentsUrl(eventId, `${commentId}/reactions/`),
        { emoji },
      );
      return mapComment(data);
    },
    onMutate: async ({ commentId, emoji }) => {
      await qc.cancelQueries({ queryKey: eventCommentKeys.list(eventId) });
      const prev = qc.getQueryData<EventCommentList>(eventCommentKeys.list(eventId));
      if (prev) {
        const nextList: EventCommentList = {
          ...prev,
          items: prev.items.map((c) => {
            const updated = toggleOnRow(c, commentId, emoji);
            return {
              ...updated,
              replies: updated.replies.map((r) => toggleOnRow(r, commentId, emoji)),
            };
          }),
        };
        qc.setQueryData(eventCommentKeys.list(eventId), nextList);
      }
      return { prev };
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) {
        qc.setQueryData(eventCommentKeys.list(eventId), ctx.prev);
      }
    },
    onSettled: () => {
      void qc.invalidateQueries({ queryKey: eventCommentKeys.list(eventId) });
    },
  });
}
