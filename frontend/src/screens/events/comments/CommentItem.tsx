import { useState } from 'react';
import { toast } from 'sonner';

import { extractApiError } from '@/api/apiErrors';
import { useDeleteComment, usePostReply, useToggleReaction } from '@/api/eventComments';
import type { EventComment, ReactionEmojiValue } from '@/models/eventComment';

import { CommentComposer } from './CommentComposer';
import { DeleteCommentDialog } from './DeleteCommentDialog';
import { ReactionBar } from './ReactionBar';
import { ReplyItem } from './ReplyItem';
import { formatRelative } from './utils';

interface Props {
  comment: EventComment;
  eventId: string;
  token?: string;
  canReact: boolean;
  canReply: boolean;
  reactDisabledReason?: string | undefined;
}

export function CommentItem({
  comment,
  eventId,
  token,
  canReact,
  canReply,
  reactDisabledReason,
}: Props) {
  const toggleReaction = useToggleReaction(eventId, token);
  const deleteComment = useDeleteComment(eventId, token);
  const postReply = usePostReply(eventId, token);
  const [replyOpen, setReplyOpen] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const handleToggle = (emoji: ReactionEmojiValue) => {
    toggleReaction.mutate({ commentId: comment.id, emoji });
  };

  const handleDelete = () => {
    deleteComment.mutate(
      { commentId: comment.id },
      {
        onSuccess: () => {
          setConfirmOpen(false);
        },
      },
    );
  };

  const handleSubmitReply = async (body: string) => {
    try {
      await postReply.mutateAsync({ parentId: comment.id, body });
      setReplyOpen(false);
    } catch (err) {
      toast.error(extractApiError(err) ?? "couldn't post your reply");
    }
  };

  return (
    <article className="flex flex-col gap-2">
      <div className="flex items-center gap-2">
        {comment.authorPhotoUrl ? (
          <img src={comment.authorPhotoUrl} alt="" className="h-8 w-8 rounded-full object-cover" />
        ) : null}
        <span className="text-sm font-medium lowercase">{comment.authorDisplayName}</span>
        <span className="text-foreground-tertiary text-xs">
          {formatRelative(comment.createdAt)}
        </span>
      </div>
      {comment.isDeleted ? (
        <p className="text-foreground-tertiary text-sm italic">[deleted]</p>
      ) : (
        <p className="text-sm whitespace-pre-wrap">{comment.body}</p>
      )}
      {!comment.isDeleted ? (
        <div className="flex items-center justify-between gap-2">
          <ReactionBar
            reactions={comment.reactions}
            canReact={canReact}
            onToggle={handleToggle}
            disabledReason={reactDisabledReason}
          />
          <div className="flex items-center gap-3">
            {canReply ? (
              <button
                type="button"
                onClick={() => {
                  setReplyOpen((v) => !v);
                }}
                className="text-foreground-tertiary text-xs hover:underline"
              >
                {replyOpen ? 'cancel' : 'reply'}
              </button>
            ) : null}
            {comment.canDelete ? (
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
        </div>
      ) : null}
      {replyOpen ? (
        <div className="ml-6">
          <CommentComposer
            onSubmit={handleSubmitReply}
            submitting={postReply.isPending}
            placeholder="reply…"
            // eslint-disable-next-line jsx-a11y/no-autofocus
            autoFocus
            label="reply"
          />
        </div>
      ) : null}
      {comment.replies.length > 0 ? (
        <div className="flex flex-col gap-2">
          {comment.replies.map((reply) => (
            <ReplyItem
              key={reply.id}
              reply={reply}
              eventId={eventId}
              {...(token ? { token } : {})}
              canReact={canReact}
              reactDisabledReason={reactDisabledReason}
            />
          ))}
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
    </article>
  );
}
