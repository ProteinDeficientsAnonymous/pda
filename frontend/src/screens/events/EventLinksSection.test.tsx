import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useMyEventFeedback } from '@/api/eventFeedbackHost';
import { setAuthed, setUnauthed } from '@/test/auth';
import { makeEvent, makeUser } from '@/test/fixtures';

import { LinksSection } from './EventMemberSection';

vi.mock('@/api/eventFeedbackHost', () => ({ useMyEventFeedback: vi.fn() }));

function mockMyFeedback(token: string | null) {
  vi.mocked(useMyEventFeedback).mockReturnValue({
    data: { token },
  } as ReturnType<typeof useMyEventFeedback>);
}

beforeEach(() => {
  setUnauthed();
  mockMyFeedback(null);
});

function renderLinks(event: ReturnType<typeof makeEvent>) {
  return render(
    <MemoryRouter>
      <LinksSection event={event} />
    </MemoryRouter>,
  );
}

describe('LinksSection', () => {
  it('renders nothing when there are no links', () => {
    const { container } = renderLinks(makeEvent());
    expect(container).toBeEmptyDOMElement();
  });
});

describe('LinksSection — leave feedback', () => {
  beforeEach(() => {
    setAuthed(makeUser());
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
    setUnauthed();
    renderLinks(makeEvent({ isPast: true }));
    expect(useMyEventFeedback).toHaveBeenLastCalledWith('ev1', false);
  });
});
