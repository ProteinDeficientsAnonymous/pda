import { useState } from 'react';

import { useDeleteComment, useToggleReaction } from '@/api/eventComments';
import type { EventCommentReply, ReactionEmojiValue } from '@/models/eventComment';

import { DeleteCommentDialog } from './DeleteCommentDialog';
import { ReactionBar } from './ReactionBar';
import { formatRelative } from './utils';

interface Props {
  reply: EventCommentReply;
  eventId: string;
  canReact: boolean;
  reactDisabledReason?: string | undefined;
}

export function ReplyItem({ reply, eventId, canReact, reactDisabledReason }: Props) {
  const toggleReaction = useToggleReaction(eventId);
  const deleteComment = useDeleteComment(eventId);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleToggle = (emoji: ReactionEmojiValue) => {
    toggleReaction.mutate({ commentId: reply.id, emoji });
  };

  const handleDelete = () => {
    deleteComment.mutate({ commentId: reply.id }, { onSuccess: () => { setConfirmOpen(false); } });
  };

  return (
    <div className="border-border-strong ml-6 border-l-2 pl-3">
      <div className="flex items-center gap-2">
        {reply.authorPhotoUrl ? (
          <img
            src={reply.authorPhotoUrl}
            alt=""
            className="h-6 w-6 rounded-full object-cover"
          />
        ) : null}
        <span className="text-sm font-medium">{reply.authorDisplayName.toLowerCase()}</span>
        <span className="text-foreground-tertiary text-xs">{formatRelative(reply.createdAt)}</span>
      </div>
      {reply.isDeleted ? (
        <p className="text-foreground-tertiary text-sm italic">[deleted]</p>
      ) : (
        <p className="text-sm whitespace-pre-wrap">{reply.body}</p>
      )}
      {!reply.isDeleted ? (
        <div className="mt-1 flex items-center justify-between gap-2">
          <ReactionBar
            reactions={reply.reactions}
            canReact={canReact}
            onToggle={handleToggle}
            disabledReason={reactDisabledReason}
          />
          {reply.canDelete ? (
            <button
              type="button"
              onClick={() => { setConfirmOpen(true); }}
              className="text-foreground-tertiary text-xs hover:underline"
            >
              delete
            </button>
          ) : null}
        </div>
      ) : null}
      <DeleteCommentDialog
        open={confirmOpen}
        onClose={() => { setConfirmOpen(false); }}
        onConfirm={handleDelete}
        submitting={deleteComment.isPending}
      />
    </div>
  );
}
