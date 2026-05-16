import type { EventComment } from '@/models/eventComment';

import { CommentItem } from './CommentItem';

interface Props {
  comments: EventComment[];
  eventId: string;
  canReact: boolean;
  canReply: boolean;
  reactDisabledReason?: string | undefined;
}

export function CommentThread({
  comments,
  eventId,
  canReact,
  canReply,
  reactDisabledReason,
}: Props) {
  if (comments.length === 0) {
    return <p className="text-foreground-tertiary text-sm">no comments yet.</p>;
  }
  return (
    <div className="flex flex-col gap-6">
      {comments.map((c) => (
        <CommentItem
          key={c.id}
          comment={c}
          eventId={eventId}
          canReact={canReact}
          canReply={canReply}
          reactDisabledReason={reactDisabledReason}
        />
      ))}
    </div>
  );
}
