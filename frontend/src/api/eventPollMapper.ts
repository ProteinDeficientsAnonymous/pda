import type {
  EventPoll,
  EventPollOption,
  PollVoter,
  VoteChoice,
} from '@/models/eventPoll';

interface WireVoter {
  user_id: string;
  name: string;
  photo_url: string;
}

interface WireOption {
  id: string;
  datetime: string;
  display_order: number;
  yes_count: number;
  maybe_count: number;
  no_count: number;
  yes_voters: WireVoter[];
  maybe_voters: WireVoter[];
  no_voters: WireVoter[];
}

export interface WireEventPoll {
  id: string;
  event_id: string;
  is_active: boolean;
  options: WireOption[];
  winning_option_id: string | null;
  winning_datetime: string | null;
  finalized_by_id: string | null;
  finalized_at: string | null;
  my_votes: Record<string, VoteChoice>;
}

function mapVoter(w: WireVoter): PollVoter {
  return { userId: w.user_id, name: w.name, photoUrl: w.photo_url };
}

function mapOption(w: WireOption): EventPollOption {
  return {
    id: w.id,
    datetime: new Date(w.datetime),
    displayOrder: w.display_order,
    yesCount: w.yes_count,
    maybeCount: w.maybe_count,
    noCount: w.no_count,
    yesVoters: w.yes_voters.map(mapVoter),
    maybeVoters: w.maybe_voters.map(mapVoter),
    noVoters: w.no_voters.map(mapVoter),
  };
}

export function mapEventPoll(w: WireEventPoll): EventPoll {
  return {
    id: w.id,
    eventId: w.event_id,
    isActive: w.is_active,
    options: w.options.map(mapOption),
    winningOptionId: w.winning_option_id,
    winningDatetime: w.winning_datetime ? new Date(w.winning_datetime) : null,
    finalizedById: w.finalized_by_id,
    finalizedAt: w.finalized_at ? new Date(w.finalized_at) : null,
    myVotes: w.my_votes,
  };
}
