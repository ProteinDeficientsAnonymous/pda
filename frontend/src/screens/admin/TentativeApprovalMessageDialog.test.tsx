import { screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from '@/auth/store';
import type { User } from '@/models/user';
import { makeUser as makeSharedUser } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import { TentativeApprovalMessageDialog } from './TentativeApprovalMessageDialog';

vi.mock('@/api/client');

vi.mock('@/api/content', () => ({
  useTentativeApprovalMessage: () => ({
    data: {
      body: 'hi ${FIRST_NAME}, from ${SENDER_NAME} — you are tentatively in. sign in: ${MAGIC_LINK}\n\nofficial lead:\n${NEXT_OFFICIAL_EVENT}\n\nclub lead:\n${CLUB_EVENT}',
      updatedAt: '2026-01-01',
    },
    isPending: false,
    isError: false,
  }),
  useUpdateTentativeApprovalMessage: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useWhatsAppLink: () => ({
    data: { link: '', updatedAt: '2026-01-01' },
    isPending: false,
    isError: false,
  }),
}));

const suggestedEvents = vi.hoisted(() => ({
  data: {
    nextOfficialEvent: null as null | {
      id: string;
      slug: string;
      title: string;
      startDatetime: Date;
    },
    clubEvent: null as null | { id: string; slug: string; title: string; startDatetime: Date },
    clubEventFromPickedClub: false,
  },
}));

vi.mock('@/api/joinSuggestedEvents', () => ({
  useJoinRequestSuggestedEvents: () => ({ ...suggestedEvents, isPending: false }),
}));

function makeUser(overrides?: Partial<User>): User {
  return makeSharedUser({
    id: 'u1',
    phoneNumber: '+12125550000',
    firstName: 'Vetter',
    lastName: 'Vee',
    fullName: 'Vetter Vee',
    ...overrides,
  });
}

beforeEach(() => {
  suggestedEvents.data = {
    nextOfficialEvent: null,
    clubEvent: null,
    clubEventFromPickedClub: false,
  };
  useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
});

function renderDialog(user: User | null, magicLinkToken: string | null = null) {
  useAuthStore.setState({
    status: user ? 'authed' : 'idle',
    user,
    accessToken: user ? 'tok' : null,
  });
  return renderWithProviders(
    <TentativeApprovalMessageDialog
      open
      onClose={() => {}}
      fullName="Sam Vetterson"
      firstName="Sam"
      phoneNumber="+12025551234"
      magicLinkToken={magicLinkToken}
      joinRequestId="jr1"
    />,
  );
}

describe('TentativeApprovalMessageDialog', () => {
  it('renders sms and whatsapp buttons with substituted hrefs, no magic link', () => {
    renderDialog(makeUser());
    const sms = screen.getByText('send via sms').closest('a');
    const wa = screen.getByText('send via whatsapp').closest('a');
    expect(sms?.getAttribute('href')).toContain('sms:+12025551234?body=');
    expect(sms?.getAttribute('href')).toContain(
      encodeURIComponent('hi Sam, from Vetter — you are tentatively in'),
    );
    expect(wa?.getAttribute('href')).toContain('https://wa.me/12025551234?text=');
    expect(screen.queryByText(/magic-login/i)).toBeNull();
    expect(screen.queryByRole('button', { name: /copy link/i })).toBeNull();
  });

  it('substitutes ${MAGIC_LINK} into the sms body when a token is present', () => {
    renderDialog(makeUser(), 'magic123');
    const sms = screen.getByText('send via sms').closest('a');
    expect(sms?.getAttribute('href')).toContain(
      encodeURIComponent(`${window.location.origin}/magic-login/magic123`),
    );
  });

  it('hides edit-template trigger without permission', () => {
    renderDialog(makeUser());
    expect(screen.queryByRole('button', { name: /edit tentative approval message/i })).toBeNull();
  });

  it('shows edit-template trigger with permission', () => {
    const user = makeUser({
      roles: [
        {
          id: 'r1',
          name: 'vetter',
          isDefault: false,
          permissions: ['approve_join_requests'],
        },
      ],
    });
    renderDialog(user);
    expect(
      screen.getByRole('button', { name: /edit tentative approval message/i }),
    ).toBeInTheDocument();
  });

  it("adds only the event details under the template's own lead-ins", () => {
    suggestedEvents.data = {
      nextOfficialEvent: {
        id: 'o1',
        slug: 'walk',
        title: 'Park Walk',
        startDatetime: new Date('2026-12-19T16:00:00Z'),
      },
      clubEvent: {
        id: 'c1',
        slug: 'book-club',
        title: 'Book Club',
        startDatetime: new Date('2026-12-10T23:30:00Z'),
      },
      clubEventFromPickedClub: true,
    };
    renderDialog(makeUser());
    const message = screen.getByText(/official lead:/);
    expect(message).toHaveTextContent(
      `official lead: Park Walk — sat dec 19, 11:00 am et ${window.location.origin}/events/walk`,
    );
    expect(message).toHaveTextContent('club lead: Book Club');
    expect(screen.queryByText(/here's/)).toBeNull();
  });

  it('leaves out the lead-in when there is no event', () => {
    suggestedEvents.data = {
      nextOfficialEvent: null,
      clubEvent: {
        id: 'c1',
        slug: 'movie-night',
        title: 'Movie Night',
        startDatetime: new Date('2026-12-10T23:30:00Z'),
      },
      clubEventFromPickedClub: false,
    };
    renderDialog(makeUser());
    expect(screen.getByText(/club lead:/)).toHaveTextContent('club lead: Movie Night');
    expect(screen.queryByText(/official lead:/)).toBeNull();
  });
});
