import { useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

import { extractApiError } from '@/api/apiErrors';
import { eventCommentKeys, useEventComments, usePostComment } from '@/api/eventComments';
import { useAuthStore } from '@/auth/store';
import { useEventSource } from '@/hooks/useEventSource';
import type { CannotPostReason } from '@/models/eventComment';

import { CommentComposer } from './CommentComposer';
import { CommentThread } from './CommentThread';

interface Props {
  eventId: string;
  token?: string;
}

function disabledReasonFor(cannot: CannotPostReason | null): string | undefined {
  if (cannot === 'login_required') return 'log in to react';
  if (cannot === 'rsvp_required') return 'rsvp to react';
  return undefined;
}

function ComposerOrPrompt({
  canPost,
  cannotPostReason,
  onSubmit,
  submitting,
}: {
  canPost: boolean;
  cannotPostReason: CannotPostReason | null | undefined;
  onSubmit: (body: string) => void | Promise<void>;
  submitting: boolean;
}) {
  if (canPost) {
    return (
      <div className="mb-4">
        <CommentComposer onSubmit={onSubmit} submitting={submitting} />
      </div>
    );
  }
  if (cannotPostReason === 'rsvp_required') {
    return <p className="text-foreground-tertiary mb-4 text-sm">rsvp to join the conversation.</p>;
  }
  return <p className="text-foreground-tertiary mb-4 text-sm">log in to comment.</p>;
}

export function EventCommentsCard({ eventId, token }: Props) {
  const { data, isPending, isError } = useEventComments(eventId, token);
  const postComment = usePostComment(eventId, token);
  const qc = useQueryClient();

  // Non-members have no NotificationBell mounted to pick up live comment updates.
  const isAuthed = useAuthStore((s) => s.status === 'authed');
  useEventSource({
    url: '/api/notifications/stream/',
    token: null,
    anonymous: !isAuthed,
    events: {
      event_updated: () => {
        void qc.invalidateQueries({ queryKey: eventCommentKeys.list(eventId) });
      },
    },
  });

  if (isPending) {
    return (
      <section className="border-border-strong bg-surface rounded-lg border p-4">
        <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">comments</h2>
        <p className="text-foreground-tertiary text-sm">loading…</p>
      </section>
    );
  }
  if (isError) {
    return (
      <section className="border-border-strong bg-surface rounded-lg border p-4">
        <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">comments</h2>
        <p className="text-foreground-tertiary text-sm">couldn't load comments — try refreshing.</p>
      </section>
    );
  }

  const canReact = data.canPost;
  const reactDisabledReason = disabledReasonFor(data.cannotPostReason);

  return (
    <section className="border-border-strong bg-surface rounded-lg border p-4">
      <h2 className="text-muted mb-3 text-xs font-medium tracking-wide">comments</h2>
      <ComposerOrPrompt
        canPost={data.canPost}
        cannotPostReason={data.cannotPostReason}
        onSubmit={async (body) => {
          try {
            await postComment.mutateAsync({ body });
          } catch (err) {
            toast.error(extractApiError(err) ?? "couldn't post your comment");
          }
        }}
        submitting={postComment.isPending}
      />
      <CommentThread
        comments={data.items}
        eventId={eventId}
        {...(token ? { token } : {})}
        canReact={canReact}
        canReply={data.canPost}
        reactDisabledReason={reactDisabledReason}
      />
    </section>
  );
}
