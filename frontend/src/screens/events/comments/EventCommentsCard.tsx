import { useEventComments, usePostComment } from '@/api/eventComments';
import type { CannotPostReason } from '@/models/eventComment';

import { CommentComposer } from './CommentComposer';
import { CommentThread } from './CommentThread';

interface Props {
  eventId: string;
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
  onSubmit: (body: string) => void;
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

export function EventCommentsCard({ eventId }: Props) {
  const { data, isPending, isError } = useEventComments(eventId);
  const postComment = usePostComment(eventId);

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
        <p className="text-foreground-tertiary text-sm">
          couldn't load comments — try refreshing.
        </p>
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
        onSubmit={(body) => { postComment.mutate({ body }); }}
        submitting={postComment.isPending}
      />
      <CommentThread
        comments={data.items}
        eventId={eventId}
        canReact={canReact}
        canReply={data.canPost}
        reactDisabledReason={reactDisabledReason}
      />
    </section>
  );
}
