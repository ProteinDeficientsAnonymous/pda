import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import type { Event } from '@/models/event';
import { RsvpServerStatus } from '@/models/event';
import { makeEvent, makeGuest } from '@/test/fixtures';

import { RsvpGuestList } from './RsvpGuestList';

function renderList(event: Event, canSeeInvited = false) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <RsvpGuestList event={event} canSeeInvited={canSeeInvited} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('RsvpGuestList summary', () => {
  it('shows going and maybe counts', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'u1', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'u2', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'u3', status: RsvpServerStatus.Maybe }),
      ],
    });
    renderList(event);
    expect(screen.getByText(/2 going/)).toBeInTheDocument();
    expect(screen.getByText(/1 maybe/)).toBeInTheDocument();
  });

  it('counts plus-ones toward the going total', () => {
    const event = makeEvent({
      guests: [makeGuest({ userId: 'u1', status: RsvpServerStatus.Attending, hasPlusOne: true })],
    });
    renderList(event);
    expect(screen.getByText(/2 going/)).toBeInTheDocument();
  });

  it('previews at most five avatars and shows the overflow count', () => {
    const guests = Array.from({ length: 8 }, (_, i) =>
      makeGuest({ userId: `u${String(i)}`, name: `Guest ${String(i)}` }),
    );
    renderList(makeEvent({ guests }));
    expect(screen.getByRole('button', { name: /view all 8 guests/i })).toHaveTextContent('+3');
  });

  it('omits the overflow bubble when everyone fits in the preview', () => {
    const guests = Array.from({ length: 3 }, (_, i) => makeGuest({ userId: `u${String(i)}` }));
    renderList(makeEvent({ guests }));
    expect(screen.queryByRole('button', { name: /view all \d+ guests/i })).not.toBeInTheDocument();
  });

  it('previews members before non-members', () => {
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'n1', name: 'Nonmember', isMember: false }),
        makeGuest({ userId: 'm1', name: 'Member', isMember: true }),
      ],
    });
    renderList(event);
    const avatars = screen.getAllByTitle(/member/i);
    expect(avatars[0]).toHaveAttribute('title', 'Member');
  });

  it('shows a genuinely-empty message when there are no attendees', () => {
    renderList(makeEvent({ guests: [], attendingCount: 0 }));
    expect(screen.getByText('no one yet')).toBeInTheDocument();
  });

  it('shows a gated message when guests are hidden but attendees exist', () => {
    renderList(makeEvent({ guests: [], attendingCount: 3 }));
    expect(screen.getByText("rsvp to see who's going")).toBeInTheDocument();
  });
});

describe('RsvpGuestList dialog', () => {
  it('opens the guest list and filters by search', async () => {
    const user = userEvent.setup();
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'u1', name: 'Alex', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'u2', name: 'Sam', status: RsvpServerStatus.Attending }),
      ],
    });
    renderList(event);
    await user.click(screen.getByRole('button', { name: 'view all' }));

    const dialog = screen.getByRole('dialog', { name: /guest list/i });
    expect(within(dialog).getByText('Alex')).toBeInTheDocument();

    await user.type(within(dialog).getByPlaceholderText('search guests'), 'ale');
    expect(within(dialog).getByText('Alex')).toBeInTheDocument();
    expect(within(dialog).queryByText('Sam')).not.toBeInTheDocument();
  });

  it('separates going and maybe into tabs', async () => {
    const user = userEvent.setup();
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'u1', name: 'Alex', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'u2', name: 'Sam', status: RsvpServerStatus.Maybe }),
      ],
    });
    renderList(event);
    await user.click(screen.getByRole('button', { name: 'view all' }));

    const dialog = screen.getByRole('dialog', { name: /guest list/i });
    expect(within(dialog).queryByText('Sam')).not.toBeInTheDocument();

    await user.click(within(dialog).getByRole('tab', { name: /maybe/i }));
    expect(within(dialog).getByText('Sam')).toBeInTheDocument();
    expect(within(dialog).queryByText('Alex')).not.toBeInTheDocument();
  });

  it('hides the cant go and waitlist tabs from a guest (Issue 1042)', async () => {
    const user = userEvent.setup();
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'u1', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'u2', status: RsvpServerStatus.CantGo }),
        makeGuest({ userId: 'u3', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    renderList(event, false);
    await user.click(screen.getByRole('button', { name: 'view all' }));

    const dialog = screen.getByRole('dialog', { name: /guest list/i });
    expect(within(dialog).queryByRole('tab', { name: /can't go/i })).not.toBeInTheDocument();
    expect(within(dialog).queryByRole('tab', { name: /waitlist/i })).not.toBeInTheDocument();
  });

  it('shows the cant go and waitlist tabs to a host (Issue 1042)', async () => {
    const user = userEvent.setup();
    const event = makeEvent({
      guests: [
        makeGuest({ userId: 'u1', status: RsvpServerStatus.Attending }),
        makeGuest({ userId: 'u2', status: RsvpServerStatus.CantGo }),
        makeGuest({ userId: 'u3', status: RsvpServerStatus.Waitlisted }),
      ],
    });
    renderList(event, true);
    await user.click(screen.getByRole('button', { name: 'view all' }));

    const dialog = screen.getByRole('dialog', { name: /guest list/i });
    expect(within(dialog).getByRole('tab', { name: /can't go/i })).toBeInTheDocument();
    expect(within(dialog).getByRole('tab', { name: /waitlist/i })).toBeInTheDocument();
  });

  it('links member guests to their profile in the dialog', async () => {
    const user = userEvent.setup();
    const event = makeEvent({
      guests: [makeGuest({ userId: 'user-1', name: 'Alex', isMember: true })],
    });
    renderList(event);
    await user.click(screen.getByRole('button', { name: 'view all' }));

    const dialog = screen.getByRole('dialog', { name: /guest list/i });
    expect(within(dialog).getByRole('link', { name: /alex/i })).toHaveAttribute(
      'href',
      '/members/user-1',
    );
  });

  it('renders non-member guests without a profile link', async () => {
    const user = userEvent.setup();
    const event = makeEvent({
      guests: [makeGuest({ userId: 'guest-1', name: 'Sam', isMember: false })],
    });
    renderList(event);
    await user.click(screen.getByRole('button', { name: 'view all' }));

    const dialog = screen.getByRole('dialog', { name: /guest list/i });
    expect(within(dialog).queryByRole('link', { name: /sam/i })).not.toBeInTheDocument();
    expect(within(dialog).getByText('Sam')).toBeInTheDocument();
  });
});
