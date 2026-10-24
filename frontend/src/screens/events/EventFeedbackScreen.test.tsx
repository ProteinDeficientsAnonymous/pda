import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useHostEventFeedback } from '@/api/eventFeedbackHost';
import { useEvent } from '@/api/events';
import { makeEvent } from '@/test/fixtures';

import EventFeedbackScreen from './EventFeedbackScreen';

vi.mock('@/api/events', () => ({ useEvent: vi.fn() }));
vi.mock('@/api/eventFeedbackHost', () => ({ useHostEventFeedback: vi.fn() }));

const question = (id: string, label: string, order: number) => ({
  id,
  label,
  field_type: 'text',
  options: [],
  required: false,
  display_order: order,
});
const QUESTIONS = [question('q1', 'How was it?', 0), question('q2', 'Rating', 1)];

function mockFeedback(value: Record<string, unknown>) {
  vi.mocked(useHostEventFeedback).mockReturnValue(
    value as unknown as ReturnType<typeof useHostEventFeedback>,
  );
}

function renderScreen() {
  return render(
    <MemoryRouter initialEntries={['/events/ev1/feedback']}>
      <Routes>
        <Route path="/events/:id/feedback" element={<EventFeedbackScreen />} />
        <Route path="/events/:id" element={<div>event detail</div>} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.mocked(useEvent).mockReturnValue({
    data: makeEvent({ title: 'Spring Potluck' }),
    isPending: false,
    isError: false,
  } as ReturnType<typeof useEvent>);
});

describe('EventFeedbackScreen', () => {
  it('lists answers under each question with the day only', () => {
    mockFeedback({
      isPending: false,
      isError: false,
      data: {
        questions: QUESTIONS,
        responses: [
          {
            id: 'r1',
            submitted_on: '2026-10-20',
            answers: {
              q1: { label: 'How was it?', answer: 'loved the soup' },
              q2: { label: 'Rating', answer: '5' },
            },
          },
          {
            id: 'r2',
            submitted_on: '2026-10-21',
            answers: { q1: { label: 'How was it?', answer: 'a bit loud' } },
          },
        ],
      },
    });
    renderScreen();

    const q1 = screen.getByRole('heading', { name: 'how was it?' }).closest('section')!;
    expect(within(q1).getByText('loved the soup')).toBeInTheDocument();
    expect(within(q1).getByText('a bit loud')).toBeInTheDocument();
    expect(within(q1).getByText('oct 20, 2026')).toBeInTheDocument();
    expect(within(q1).getByText('oct 21, 2026')).toBeInTheDocument();

    const q2 = screen.getByRole('heading', { name: 'rating' }).closest('section')!;
    expect(within(q2).getByText('5')).toBeInTheDocument();
    expect(within(q2).queryByText('a bit loud')).not.toBeInTheDocument();
  });

  it('shows an empty state when nobody has responded', () => {
    mockFeedback({
      isPending: false,
      isError: false,
      data: { questions: QUESTIONS, responses: [] },
    });
    renderScreen();

    expect(screen.getByText('no feedback yet 🌿')).toBeInTheDocument();
  });

  it('tells non-hosts they cannot see feedback', () => {
    mockFeedback({
      isPending: false,
      isError: true,
      error: { isAxiosError: true, response: { status: 403, data: {} } },
    });
    renderScreen();

    expect(screen.getByRole('alert')).toHaveTextContent(/host or a co-host/i);
  });

  it('links back to the event', async () => {
    mockFeedback({ isPending: false, isError: false, data: { questions: [], responses: [] } });
    renderScreen();

    await userEvent.click(screen.getByRole('link', { name: /back to event/i }));

    expect(screen.getByText('event detail')).toBeInTheDocument();
  });
});
