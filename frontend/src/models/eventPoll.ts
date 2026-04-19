// Domain types for the datetime-poll feature. Backend schemas at
// backend/community/_event_poll_schemas.py.

export enum VoteChoice {
  Yes = 'yes',
  Maybe = 'maybe',
  No = 'no',
}

export const ALL_VOTE_CHOICES: readonly VoteChoice[] = [
  VoteChoice.Yes,
  VoteChoice.Maybe,
  VoteChoice.No,
];

export interface PollVoter {
  userId: string;
  name: string;
  photoUrl: string;
}

export interface EventPollOption {
  id: string;
  datetime: Date;
  displayOrder: number;
  yesCount: number;
  maybeCount: number;
  noCount: number;
  yesVoters: readonly PollVoter[];
  maybeVoters: readonly PollVoter[];
  noVoters: readonly PollVoter[];
}

export interface EventPoll {
  id: string;
  eventId: string;
  isActive: boolean;
  options: readonly EventPollOption[];
  winningOptionId: string | null;
  winningDatetime: Date | null;
  finalizedById: string | null;
  finalizedAt: Date | null;
  myVotes: Readonly<Record<string, VoteChoice>>;
}
