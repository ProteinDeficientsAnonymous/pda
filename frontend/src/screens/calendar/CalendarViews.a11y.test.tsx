import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { axe } from 'vitest-axe';
import type { Event } from '@/models/event';
import { EventStatus, EventType, EventVisibility, InvitePermission } from '@/models/event';
import { AgendaList } from './AgendaList';
import { DayEventList } from './DayEventList';

function makeEvent(overrides: Partial<Event> = {}): Event {
  const start = new Date();
  start.setDate(start.getDate() + 7);
  return {
    id: 'ev1',
    title: 'potluck in the park',
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
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    eventType: EventType.Community,
    visibility: EventVisibility.Public,
    photoUrl: '',
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

describe('calendar views accessibility', () => {
  it('AgendaList exposes each event as a button labelled with its title', () => {
    const events = [
      makeEvent({ id: 'a', title: 'movie night' }),
      makeEvent({ id: 'b', title: 'beach cleanup' }),
    ];
    render(<AgendaList events={events} onSelectEvent={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'movie night' })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'beach cleanup' })).toBeInTheDocument();
  });

  it('AgendaList has no axe violations with events', async () => {
    const events = [makeEvent()];
    const { container } = render(<AgendaList events={events} onSelectEvent={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('AgendaList empty state has no axe violations', async () => {
    const { container } = render(<AgendaList events={[]} onSelectEvent={vi.fn()} />);
    expect(await axe(container)).toHaveNoViolations();
  });

  it('DayEventList exposes each event as a button labelled with its title', () => {
    const target = new Date();
    target.setHours(18, 0, 0, 0);
    const events = [makeEvent({ id: 'a', title: 'dinner', startDatetime: target })];

    render(<DayEventList date={target} events={events} onSelectEvent={vi.fn()} />);

    expect(screen.getByRole('button', { name: 'dinner' })).toBeInTheDocument();
  });
});
