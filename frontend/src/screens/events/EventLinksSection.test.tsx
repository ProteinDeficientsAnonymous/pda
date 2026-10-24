import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useMyEventFeedback } from '@/api/eventFeedbackHost';
import { useAuthStore } from '@/auth/store';
import { makeEvent, makeUser } from '@/test/fixtures';

import { LinksSection } from './EventMemberSection';

vi.mock('@/api/eventFeedbackHost', () => ({ useMyEventFeedback: vi.fn() }));

function mockMyFeedback(token: string | null) {
  vi.mocked(useMyEventFeedback).mockReturnValue({
    data: { token },
  } as ReturnType<typeof useMyEventFeedback>);
}

beforeEach(() => {
  useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
  mockMyFeedback(null);
});

function renderLinks(event: ReturnType<typeof makeEvent>) {
  return render(
    <MemoryRouter>
      <LinksSection event={event} />
    </MemoryRouter>,
  );
}

describe('LinksSection — linked surveys (Issue 1463)', () => {
  it('renders nothing when there are no links or surveys', () => {
    const { container } = renderLinks(makeEvent());
    expect(container).toBeEmptyDOMElement();
  });

  it('names each linked survey and links to it', () => {
    renderLinks(
      makeEvent({
        linkedSurveys: [{ id: 's1', title: 'Potluck Feedback', slug: 'potluck-feedback' }],
      }),
    );

    const link = screen.getByRole('link', { name: 'potluck feedback' });
    expect(link).toHaveAttribute('href', '/surveys/potluck-feedback');
  });

  it('excludes the datetime poll from the links card', () => {
    renderLinks(
      makeEvent({
        datetimePollSlug: 'when-poll',
        linkedSurveys: [
          { id: 's1', title: 'When Poll', slug: 'when-poll' },
          { id: 's2', title: 'Feedback', slug: 'feedback' },
        ],
      }),
    );

    expect(screen.queryByRole('link', { name: 'when poll' })).not.toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'feedback' })).toBeInTheDocument();
  });
});

describe('LinksSection — leave feedback', () => {
  beforeEach(() => {
    useAuthStore.setState({ status: 'authed', user: makeUser(), accessToken: 'tok' });
  });

  it('links to the feedback page with the token in the fragment', () => {
    mockMyFeedback('tok-123');
    renderLinks(makeEvent({ isPast: true }));

    const link = screen.getByRole('link', { name: 'leave feedback' });
    expect(link).toHaveAttribute('href', '/feedback#tok-123');
  });

  it('hides the link when there is no pending feedback request', () => {
    renderLinks(makeEvent({ isPast: true }));

    expect(screen.queryByRole('link', { name: 'leave feedback' })).not.toBeInTheDocument();
  });

  it('only asks for the token once the viewer is signed in and the event is over', () => {
    renderLinks(makeEvent({ isPast: false }));
    expect(useMyEventFeedback).toHaveBeenLastCalledWith('ev1', false);
  });

  it('does not ask for the token when signed out, even on a past event', () => {
    useAuthStore.setState({ status: 'unauthed', user: null, accessToken: null });
    renderLinks(makeEvent({ isPast: true }));
    expect(useMyEventFeedback).toHaveBeenLastCalledWith('ev1', false);
  });
});
