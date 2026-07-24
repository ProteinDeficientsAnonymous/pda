import type {
  CommentReactionSummary,
  CommentReactor,
  EventComment,
  EventCommentList,
  EventCommentReply,
  ReactionEmojiValue,
} from '@/models/eventComment';

interface WireReactor {
  user_id: string;
  name: string;
  photo_url: string;
}

interface WireSummary {
  emoji: string;
  count: number;
  reacted_by_me: boolean;
  reactors: WireReactor[];
}

interface WireReply {
  id: string;
  author_id: string;
  author_display_name: string;
  author_photo_url: string;
  body: string;
  is_deleted: boolean;
  created_at: string;
  reactions: WireSummary[];
  can_delete: boolean;
}

interface WireComment extends WireReply {
  replies: WireReply[];
}

export interface WireCommentList {
  items: WireComment[];
  can_post: boolean;
  cannot_post_reason?: ('login_required' | 'rsvp_required') | null;
}

function mapReactor(wire: WireReactor): CommentReactor {
  return {
    userId: wire.user_id,
    name: wire.name,
    photoUrl: wire.photo_url,
  };
}

function mapSummary(wire: WireSummary): CommentReactionSummary {
  return {
    emoji: wire.emoji as ReactionEmojiValue,
    count: wire.count,
    reactedByMe: wire.reacted_by_me,
    reactors: wire.reactors.map(mapReactor),
  };
}

export function mapReply(wire: WireReply): EventCommentReply {
  return {
    id: wire.id,
    authorId: wire.author_id,
    authorDisplayName: wire.author_display_name,
    authorPhotoUrl: wire.author_photo_url,
    body: wire.body,
    isDeleted: wire.is_deleted,
    createdAt: wire.created_at,
    reactions: wire.reactions.map(mapSummary),
    canDelete: wire.can_delete,
  };
}

export function mapComment(wire: WireComment): EventComment {
  return {
    ...mapReply(wire),
    replies: wire.replies.map(mapReply),
  };
}

export function mapCommentList(wire: WireCommentList): EventCommentList {
  return {
    items: wire.items.map(mapComment),
    canPost: wire.can_post,
    cannotPostReason: wire.cannot_post_reason ?? null,
  };
}
