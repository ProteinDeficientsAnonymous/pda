import { render } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import type { PublicRsvpOut } from '@/api/publicRsvp';
import {
  type Event,
  EventStatus,
  EventType,
  EventVisibility,
  InvitePermission,
} from '@/models/event';

vi.mock('@/api/publicRsvp', () => ({
  useSubmitPublicRsvp: () => ({ mutateAsync: vi.fn(), isPending: false }),
}));

import { PublicRsvpConfirmation } from './PublicRsvpConfirmation';
import { PublicRsvpForm } from './PublicRsvpForm';

function makeEvent(overrides: Partial<Event> = {}): Event {
  return {
    id: 'ev1',
    title: 'Potluck',
    description: '',
    startDatetime: new Date('2099-06-01T18:00:00Z'),
    endDatetime: null,
    location: '123 Main St',
    latitude: null,
    longitude: null,
    whatsappLink: 'https://chat.whatsapp.com/abc123',
    partifulLink: '',
    otherLink: '',
    venmoLink: '',
    cashappLink: '',
    zelleInfo: '',
    price: '',
    rsvpEnabled: true,
    allowPlusOnes: true,
    maxAttendees: null,
    attendingCount: 0,
    waitlistedCount: 0,
    invitedCount: 0,
    datetimeTbd: false,
    hasPoll: false,
    datetimePollSlug: null,
    createdById: null,
    createdByName: null,
    createdByPhotoUrl: '',
    coHostIds: [],
    coHostNames: [],
    coHostPhotoUrls: [],
    coHostInviteIds: [],
    guests: [],
    myRsvp: null,
    surveySlugs: [],
    invitedUserIds: [],
    invitedUserNames: [],
    invitedUserPhotoUrls: [],
    invitePermission: InvitePermission.AllMembers,
    pendingCohostInvites: [],
    myPendingCohostInviteId: null,
    eventType: EventType.Official,
    visibility: EventVisibility.Public,
    photoUrl: '',
    photoUpdatedAt: null,
    tags: [],
    isPast: false,
    status: EventStatus.Active,
    ...overrides,
  };
}

describe('public rsvp a11y', () => {
  it('form has no axe violations', async () => {
    const { container } = render(
      <MemoryRouter>
        <PublicRsvpForm event={makeEvent()} onSuccess={vi.fn()} />
      </MemoryRouter>,
    );
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);

  it('confirmation has no axe violations', async () => {
    const result: PublicRsvpOut = {
      event: { id: 'ev1' } as never,
      rsvp: { status: 'attending', has_plus_one: false },
    };
    const { container } = render(
      <MemoryRouter>
        <PublicRsvpConfirmation event={makeEvent()} result={result} />
      </MemoryRouter>,
    );
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);
});
