export const ReactionEmoji = {
  Heart: '❤️',
  Joy: '😂',
  Seedling: '🌱',
  Fire: '🔥',
  ThumbsUp: '👍',
  Sob: '😭',
} as const;

export type ReactionEmojiValue = (typeof ReactionEmoji)[keyof typeof ReactionEmoji];

export const REACTION_EMOJI_ORDER: ReactionEmojiValue[] = [
  ReactionEmoji.Heart,
  ReactionEmoji.Joy,
  ReactionEmoji.Seedling,
  ReactionEmoji.Fire,
  ReactionEmoji.ThumbsUp,
  ReactionEmoji.Sob,
];

export interface CommentReactor {
  userId: string;
  name: string;
  photoUrl: string;
}

export interface CommentReactionSummary {
  emoji: ReactionEmojiValue;
  count: number;
  reactedByMe: boolean;
  reactors: readonly CommentReactor[];
}

export interface EventCommentReply {
  id: string;
  authorId: string;
  authorDisplayName: string;
  authorPhotoUrl: string;
  body: string;
  isDeleted: boolean;
  createdAt: string; // ISO string
  reactions: CommentReactionSummary[];
  canDelete: boolean;
}

export interface EventComment extends EventCommentReply {
  replies: EventCommentReply[];
}

export type CannotPostReason = 'login_required' | 'rsvp_required';

export interface EventCommentList {
  items: EventComment[];
  canPost: boolean;
  cannotPostReason: CannotPostReason | null;
}
