import type { EventComment } from '@/models/eventComment';

import { CommentItem } from './CommentItem';

interface Props {
  comments: EventComment[];
  eventId: string;
  token?: string;
}

export function CommentThread({ comments, eventId, token }: Props) {
  if (comments.length === 0) {
    return <p className="text-foreground-tertiary text-sm">no comments yet.</p>;
  }
  return (
    <div className="flex flex-col gap-6">
      {comments.map((c) => (
        <CommentItem key={c.id} comment={c} eventId={eventId} {...(token ? { token } : {})} />
      ))}
    </div>
  );
}
