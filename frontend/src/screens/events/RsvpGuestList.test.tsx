import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { RsvpGuestList } from './RsvpGuestList';

function renderList(event: Event) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RsvpGuestList event={event} canSeeInvited={false} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('RsvpGuestList', () => {
  it('links member guests to their profile', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'user-1', name: 'Alex', isMember: true })],
    });
    renderList(event);
    const link = screen.getByRole('link', { name: /alex/i });
    expect(link).toHaveAttribute('href', '/members/user-1');
  });

  it('renders non-member guests without a profile link', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'guest-1', name: 'Sam', isMember: false, hasPlusOne: true })],
    });
    renderList(event);
    expect(screen.queryByRole('link', { name: /sam/i })).not.toBeInTheDocument();
    expect(screen.getByText('Sam')).toBeInTheDocument();
  });
});

describe('RsvpGuestList — cant go / waitlist visibility (Issue 1042)', () => {
  it('hides the cant go and waitlist tabs from a guest', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'user-1', status: RsvpServerStatus.CantGo }),
        makeGuest({ userId: 'user-2', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <MemoryRouter>
          <RsvpGuestList event={event} canSeeInvited={false} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.queryByRole('tab', { name: /can't go/i })).not.toBeInTheDocument();
    expect(screen.queryByRole('tab', { name: /waitlist/i })).not.toBeInTheDocument();
  });

  it('shows the cant go and waitlist tabs to a host', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'user-1', status: RsvpServerStatus.CantGo }),
        makeGuest({ userId: 'user-2', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    render(
      <QueryClientProvider
        client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
      >
        <MemoryRouter>
          <RsvpGuestList event={event} canSeeInvited={true} />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    expect(screen.getByRole('tab', { name: /can't go/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /waitlist/i })).toBeInTheDocument();
  });
});
