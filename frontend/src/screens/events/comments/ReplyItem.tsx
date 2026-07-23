import { useState } from 'react';

import { useDeleteComment, useToggleReaction } from '@/api/eventComments';
import type { EventCommentReply, ReactionEmojiValue } from '@/models/eventComment';

import { DeleteCommentDialog } from './DeleteCommentDialog';
import { ReactionBar } from './ReactionBar';
import { formatRelative } from './utils';

interface Props {
  reply: EventCommentReply;
  eventId: string;
  token?: string;
  canReact: boolean;
  reactDisabledReason?: string | undefined;
}

export function ReplyItem({ reply, eventId, token, canReact, reactDisabledReason }: Props) {
  const toggleReaction = useToggleReaction(eventId, token);
  const deleteComment = useDeleteComment(eventId, token);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleToggle = (emoji: ReactionEmojiValue) => {
    toggleReaction.mutate({ commentId: reply.id, emoji });
  };

  const handleDelete = () => {
    deleteComment.mutate(
      { commentId: reply.id },
      {
        onSuccess: () => {
          setConfirmOpen(false);
        },
      },
    );
  };

  return (
    <div className="ml-4 flex items-stretch gap-2">
      <ReplyConnector />
      <div className="min-w-0 flex-1 pt-3">
        <div className="flex items-center gap-2">
          {reply.authorPhotoUrl ? (
            <img src={reply.authorPhotoUrl} alt="" className="h-6 w-6 rounded-full object-cover" />
          ) : null}
          <span className="text-sm font-medium lowercase">{reply.authorDisplayName}</span>
          <span className="text-foreground-tertiary text-xs">
            {formatRelative(reply.createdAt)}
          </span>
        </div>
        {reply.isDeleted ? (
          <p className="text-foreground-tertiary text-sm italic">[deleted]</p>
        ) : (
          <p className="text-sm [overflow-wrap:anywhere] break-words whitespace-pre-wrap">
            {reply.body}
          </p>
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
                onClick={() => {
                  setConfirmOpen(true);
                }}
                className="text-foreground-tertiary text-xs hover:underline"
              >
                delete
              </button>
            ) : null}
          </div>
        ) : null}
        <DeleteCommentDialog
          open={confirmOpen}
          onClose={() => {
            setConfirmOpen(false);
          }}
          onConfirm={handleDelete}
          submitting={deleteComment.isPending}
        />
      </div>
    </div>
  );
}

function ReplyConnector() {
  return (
    <svg
      aria-hidden="true"
      width="20"
      height="100%"
      viewBox="0 0 20 40"
      preserveAspectRatio="none"
      className="text-border-strong shrink-0"
    >
      <path
        d="M 8 0 V 18 Q 8 28 18 28"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
      />
    </svg>
  );
}
