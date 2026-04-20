import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi } from 'vitest';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';
import { AgendaList } from './AgendaList';

function makeEvent(overrides: Partial<Event> = {}): Event {
  const start = new Date();
  start.setDate(start.getDate() + 7);
  return {
    id: 'ev1',
    title: 'potluck',
    description: '',
    startDatetime: start,
    endDatetime: null,
    location: '',
    latitude: null,
    longitude: null,
    whatsappLink: '',
    partifulLink: '',
    otherLink: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    price: '',
    rsvpEnabled: false,
    allowPlusOnes: false,
    maxAttendees: null,
    attendingCount: 0,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: 'u1',
    createdByName: 'Host',
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    guests: [],
    myRsvp: null,
    surveySlugs: [],
    invitedUserIds: [],
    invitedUserNames: [],
    invitedUserPhotoUrls: [],
    invitePermission: InvitePermission.CoHostsOnly,
    eventType: EventType.Community,
    visibility: EventVisibility.Public,
    photoUrl: '',
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

describe('AgendaList type filter', () => {
  const events = [
    makeEvent({ id: 'a', title: 'official meeting', eventType: EventType.Official }),
    makeEvent({ id: 'b', title: 'community picnic', eventType: EventType.Community }),
  ];

  it('defaults to showing all event types', () => {
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'official meeting' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'community picnic' })).toBeInTheDocument();
  });

  it('filters to pda official only', async () => {
    const user = userEvent.setup();
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    await user.click(screen.getByRole('radio', { name: 'pda official' }));
    expect(screen.getByRole('button', { name: 'official meeting' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'community picnic' })).not.toBeInTheDocument();
  });

  it('filters to community only', async () => {
    const user = userEvent.setup();
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    await user.click(screen.getByRole('radio', { name: 'community' }));
    expect(screen.queryByRole('button', { name: 'official meeting' })).not.toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'community picnic' })).toBeInTheDocument();
  });

  it('shows a filter-aware empty state when no events match', async () => {
    const user = userEvent.setup();
    const communityOnly = [makeEvent({ eventType: EventType.Community })];
    render(<AgendaList events={communityOnly} onSelectEvent={vi.fn()} />);
    await user.click(screen.getByRole('radio', { name: 'pda official' }));
    expect(screen.getByText('no pda official events coming up')).toBeInTheDocument();
  });
});
