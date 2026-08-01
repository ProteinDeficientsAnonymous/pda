import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { EventRsvpResponsesSection } from './EventRsvpResponsesSection';

describe('EventRsvpResponsesSection', () => {
  it('renders nothing when the event has no questions', () => {
    const { container } = render(
      <EventRsvpResponsesSection event={makeEvent({ rsvpQuestions: [] })} />,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('shows per-guest answers and choice tallies', () => {
    const event = makeEvent({
      rsvpQuestions: [
        {
          id: 'q1',
          label: 'how are you getting there?',
          fieldType: 'select_one',
          options: ['driving', 'transit'],
          required: true,
        },
        {
          id: 'q2',
          label: 'notes',
          fieldType: 'free_response',
          options: [],
          required: false,
        },
      ],
      guests: [
        makeGuest({
          userId: 'a',
          name: 'alice',
          status: RsvpServerStatus.Attending,
          answers: {
            q1: { label: 'how are you getting there?', answer: 'driving' },
            q2: { label: 'notes', answer: 'bringing chips' },
          },
        }),
        makeGuest({
          userId: 'b',
          name: 'bob',
          status: RsvpServerStatus.Maybe,
          answers: {
            q1: { label: 'how are you getting there?', answer: 'transit' },
          },
        }),
        makeGuest({
          userId: 'c',
          name: 'cara',
          status: RsvpServerStatus.CantGo,
          answers: {},
        }),
      ],
    });

    render(<EventRsvpResponsesSection event={event} />);

    expect(screen.getByRole('heading', { name: /question responses/i })).toBeInTheDocument();
    expect(screen.getByText('2 guests with going / maybe / waitlist')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.queryByText('cara')).not.toBeInTheDocument();
    expect(screen.getByText('bringing chips')).toBeInTheDocument();
    const tallies = screen.getByRole('list');
    expect(tallies).toHaveTextContent(/driving\s*1/);
    expect(tallies).toHaveTextContent(/transit\s*1/);
  });

  it('shows empty state when no going/maybe guests', () => {
    render(
      <EventRsvpResponsesSection
        event={makeEvent({
          rsvpQuestions: [
            {
              id: 'q1',
              label: 'q',
              fieldType: 'free_response',
              options: [],
              required: false,
            },
          ],
          guests: [makeGuest({ status: RsvpServerStatus.CantGo })],
        })}
      />,
    );
    expect(screen.getByText('no responses yet')).toBeInTheDocument();
  });
});
