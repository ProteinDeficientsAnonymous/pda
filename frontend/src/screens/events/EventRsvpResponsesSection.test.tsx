import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { QuestionType } from '@/api/questionTypes';
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
          fieldType: QuestionType.Select,
          options: ['driving', 'transit'],
          required: true,
        },
        {
          id: 'q2',
          label: 'notes',
          fieldType: QuestionType.Textarea,
          options: [],
          required: false,
        },
      ],
      guests: [
        makeGuest({
          userId: 'a',
          name: 'alice',
          status: RsvpServerStatus.Attending,
          questionnaireResponses: {
            q1: { label: 'how are you getting there?', answer: 'driving' },
            q2: { label: 'notes', answer: 'bringing chips' },
          },
        }),
        makeGuest({
          userId: 'b',
          name: 'bob',
          status: RsvpServerStatus.Waitlisted,
          questionnaireResponses: {
            q1: { label: 'how are you getting there?', answer: 'transit' },
          },
        }),
        makeGuest({
          userId: 'c',
          name: 'cara',
          status: RsvpServerStatus.Maybe,
          questionnaireResponses: {
            q1: { label: 'how are you getting there?', answer: 'bike' },
          },
        }),
        makeGuest({
          userId: 'd',
          name: 'dana',
          status: RsvpServerStatus.CantGo,
          questionnaireResponses: {},
        }),
      ],
    });

    render(<EventRsvpResponsesSection event={event} />);

    expect(screen.getByRole('heading', { name: /question responses/i })).toBeInTheDocument();
    expect(screen.getByText('2 guests going or waitlisted')).toBeInTheDocument();
    expect(screen.getByText('alice')).toBeInTheDocument();
    expect(screen.getByText('bob')).toBeInTheDocument();
    expect(screen.queryByText('cara')).not.toBeInTheDocument();
    expect(screen.queryByText('dana')).not.toBeInTheDocument();
    expect(screen.getByText('bringing chips')).toBeInTheDocument();
    const tallies = screen.getByRole('list');
    expect(tallies).toHaveTextContent(/driving\s*1/);
    expect(tallies).toHaveTextContent(/transit\s*1/);
    expect(tallies).not.toHaveTextContent(/bike/);
  });

  it('shows empty state when no going or waitlisted guests', () => {
    render(
      <EventRsvpResponsesSection
        event={makeEvent({
          rsvpQuestions: [
            {
              id: 'q1',
              label: 'q',
              fieldType: QuestionType.Textarea,
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

  it('keeps deleted-question answers visible via snapshot labels', () => {
    render(
      <EventRsvpResponsesSection
        event={makeEvent({
          rsvpQuestions: [],
          guests: [
            makeGuest({
              userId: 'a',
              name: 'alice',
              status: RsvpServerStatus.Attending,
              questionnaireResponses: {
                orphan: { label: 'old dietary question', answer: 'vegan' },
              },
            }),
          ],
        })}
      />,
    );
    expect(screen.getByText('old dietary question')).toBeInTheDocument();
    expect(screen.getByText('vegan')).toBeInTheDocument();
  });

  it('shows answers under the current question when the snapshot label differs', () => {
    render(
      <EventRsvpResponsesSection
        event={makeEvent({
          rsvpQuestions: [
            {
              id: 'q1',
              label: 'new question',
              fieldType: QuestionType.Textarea,
              options: [],
              required: false,
            },
          ],
          guests: [
            makeGuest({
              userId: 'a',
              name: 'alice',
              questionnaireResponses: {
                q1: { label: 'old question', answer: 'old answer' },
              },
            }),
          ],
        })}
      />,
    );

    expect(screen.getByText('new question')).toBeInTheDocument();
    expect(screen.queryByText('old question')).not.toBeInTheDocument();
    expect(screen.getByText('old answer')).toBeInTheDocument();
  });

  it('tallies choice answers even when the snapshot label was renamed', () => {
    render(
      <EventRsvpResponsesSection
        event={makeEvent({
          rsvpQuestions: [
            {
              id: 'q1',
              label: 'transport now',
              fieldType: QuestionType.Select,
              options: ['driving', 'transit'],
              required: true,
            },
          ],
          guests: [
            makeGuest({
              userId: 'a',
              name: 'alice',
              status: RsvpServerStatus.Attending,
              questionnaireResponses: {
                q1: { label: 'transport before', answer: 'driving' },
              },
            }),
          ],
        })}
      />,
    );

    expect(screen.getByRole('list')).toHaveTextContent(/driving\s*1/);
  });
});
