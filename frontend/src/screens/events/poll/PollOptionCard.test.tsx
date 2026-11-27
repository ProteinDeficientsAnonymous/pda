import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import type { EventPollOption } from '@/models/eventPoll';

import { PollOptionCard } from './PollOptionCard';

const option: EventPollOption = {
  id: 'o1',
  datetime: new Date('2030-06-15T23:00:00Z'),
  displayOrder: 0,
  yesCount: 2,
  maybeCount: 1,
  noCount: 0,
  yesVoters: [],
  maybeVoters: [],
  noVoters: [],
};

describe('PollOptionCard', () => {
  it('shows the option time in et', () => {
    render(<PollOptionCard option={option} isWinner={false} isFinalized={false} />);
    expect(
      screen.getByRole('button', { name: 'sat jun 15 7:00 pm et — 2 yes, 1 maybe, 0 no' }),
    ).toBeInTheDocument();
  });
});
