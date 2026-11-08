import { screen } from '@testing-library/react';
import { Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useEvent } from '@/api/events';
import { Code } from '@/api/validationCodes';
import { apiError } from '@/test/apiError';
import { setAuthed } from '@/test/auth';
import { creator, makeEvent, makeGuest, nonHost } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import EventQuestionResponsesScreen from './EventQuestionResponsesScreen';

vi.mock('@/api/events', () => ({
  useEvent: vi.fn(),
  eventKeys: { all: ['events'], list: vi.fn(), detail: vi.fn() },
}));

const BASE_EVENT = makeEvent({
  title: 'Spring Potluck',
  createdById: 'user-creator',
  coHostIds: ['user-creator'],
  guests: [],
});

function renderScreen() {
  return renderWithProviders(
    <Routes>
      <Route path="/events/:id/responses" element={<EventQuestionResponsesScreen />} />
      <Route path="/events/:id" element={<div>event detail</div>} />
    </Routes>,
    { route: '/events/ev1/responses' },
  );
}

beforeEach(() => {
  vi.mocked(useEvent).mockReturnValue({
    data: BASE_EVENT,
    isPending: false,
    isError: false,
  } as ReturnType<typeof useEvent>);
});

describe('EventQuestionResponsesScreen', () => {
  it('shows the forbidden notice on a 403', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: apiError(403, Code.Event.PermDenied),
    } as unknown as ReturnType<typeof useEvent>);
    renderScreen();

    expect(screen.getByText("you don't have permission to see this event")).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'back to event' })).toHaveAttribute(
      'href',
      '/events/ev1',
    );
  });

  it('shows a forbidden notice for a non-host', () => {
    setAuthed(nonHost);
    renderScreen();

    expect(screen.getByText(/only the host or a co-host/i)).toBeInTheDocument();
  });

  it('shows a notice when the event has no questions', () => {
    setAuthed(creator);
    renderScreen();

    expect(screen.getByText(/no rsvp questions/i)).toBeInTheDocument();
  });

  it('shows responses on a past event with rsvps off', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        isPast: true,
        rsvpEnabled: false,
        rsvpQuestions: [
          {
            id: 'q1',
            label: 'dietary?',
            fieldType: 'textarea',
            options: [],
            required: false,
          },
        ],
        guests: [
          makeGuest({ questionnaireResponses: { q1: { label: 'dietary?', answer: 'no nuts' } } }),
        ],
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    setAuthed(creator);
    renderScreen();

    expect(screen.getByRole('heading', { name: /question responses/i })).toBeInTheDocument();
    expect(screen.getByText('no nuts')).toBeInTheDocument();
  });

  it('shows saved answers for deleted questions', () => {
    vi.mocked(useEvent).mockReturnValue({
      data: makeEvent({
        createdById: 'user-creator',
        coHostIds: ['user-creator'],
        rsvpQuestions: [],
        guests: [
          makeGuest({
            questionnaireResponses: {
              deleted: { label: 'deleted question', answer: 'saved answer' },
            },
          }),
        ],
      }),
      isPending: false,
      isError: false,
    } as ReturnType<typeof useEvent>);
    setAuthed(creator);
    renderScreen();

    expect(screen.getByText('saved answer')).toBeInTheDocument();
  });
});
