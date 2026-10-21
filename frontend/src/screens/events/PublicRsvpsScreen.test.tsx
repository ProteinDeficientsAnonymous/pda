import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import type { ManageRsvps } from '@/api/publicRsvp';
import { eventPath, RsvpServerStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

import PublicRsvpsScreen from './PublicRsvpsScreen';

const resendAsync = vi.hoisted(() => vi.fn());
const usePublicMyRsvps = vi.hoisted(() => vi.fn());
const useResendPublicRsvpManageLink = vi.hoisted(() => vi.fn());

vi.mock('@/api/publicRsvp', () => ({
  usePublicMyRsvps: (token: string) => usePublicMyRsvps(token) as unknown,
  useResendPublicRsvpManageLink: () => useResendPublicRsvpManageLink() as unknown,
}));

vi.mock('@/api/featureFlags', () => ({ useFlag: () => false }));

// jsdom's default Storage isn't wired up for get/set round-trips — stub a real one.
const storageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string): string | null => store[key] ?? null,
    setItem: (key: string, value: string): void => {
      store[key] = value;
    },
    removeItem: (key: string): void => {
      delete store[key];
    },
    clear: (): void => {
      store = {};
    },
    get length(): number {
      return Object.keys(store).length;
    },
    key: (index: number): string | null => Object.keys(store)[index] ?? null,
  };
})();
Object.defineProperty(window, 'localStorage', { value: storageMock, writable: true });

function renderAt(token: string | null) {
  const path = token === null ? '/my-rsvps' : `/my-rsvps?token=${token}`;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <Routes>
        <Route path="/my-rsvps" element={<PublicRsvpsScreen />} />
        <Route path="/calendar" element={<p>calendar page</p>} />
      </Routes>
    </MemoryRouter>,
  );
}

function successData(overrides: Partial<ManageRsvps> = {}): ManageRsvps {
  return {
    user: { name: 'sam green', email: 's@x.com', phoneNumber: '+14155550001' },
    rsvps: [
      {
        event: makeEvent({ id: 'ev1', title: 'potluck', allowPlusOnes: true }),
        status: RsvpServerStatus.Attending,
        hasPlusOne: false,
      },
    ],
    ...overrides,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  localStorage.clear();
  resendAsync.mockResolvedValue({ detail: 'sent' });
  useResendPublicRsvpManageLink.mockReturnValue({
    mutateAsync: resendAsync,
    isPending: false,
    isSuccess: false,
    data: undefined,
  });
});

describe('PublicRsvpsScreen', () => {
  it('renders the rsvp list when the token is valid', () => {
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt('good-token');
    const link = screen.getByRole('link', { name: /potluck/ });
    expect(link).toHaveAttribute('href', eventPath(makeEvent({ id: 'ev1', title: 'potluck' })));
    expect(screen.queryByRole('heading', { name: 'your rsvps' })).not.toBeInTheDocument();
    expect(screen.getByText('sam green')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'cancel rsvp' })).not.toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'maybe' })).not.toBeInTheDocument();
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
  });

  it('sorts rsvps by start date ascending with tbd last', () => {
    usePublicMyRsvps.mockReturnValue({
      data: successData({
        rsvps: [
          {
            event: makeEvent({
              id: 'e3',
              title: 'tbd one',
              startDatetime: null,
              datetimeTbd: true,
            }),
            status: RsvpServerStatus.Attending,
            hasPlusOne: false,
          },
          {
            event: makeEvent({
              id: 'e2',
              title: 'later one',
              startDatetime: new Date('2030-02-01T12:00:00Z'),
            }),
            status: RsvpServerStatus.Attending,
            hasPlusOne: false,
          },
          {
            event: makeEvent({
              id: 'e1',
              title: 'sooner one',
              startDatetime: new Date('2030-01-01T12:00:00Z'),
            }),
            status: RsvpServerStatus.Attending,
            hasPlusOne: false,
          },
        ],
      }),
      isPending: false,
      isError: false,
    });
    renderAt('good-token');
    const titles = screen.getAllByRole('link').map((l) => l.textContent ?? '');
    expect(titles[0]).toContain('sooner one');
    expect(titles[1]).toContain('later one');
    expect(titles[2]).toContain('tbd one');
  });

  it('omits cant_go rsvps but keeps maybe and waitlisted', () => {
    const row = (
      id: string,
      title: string,
      status: (typeof RsvpServerStatus)[keyof typeof RsvpServerStatus],
    ) => ({
      event: makeEvent({ id, title }),
      status,
      hasPlusOne: false,
    });
    usePublicMyRsvps.mockReturnValue({
      data: successData({
        rsvps: [
          row('a', 'going one', RsvpServerStatus.Attending),
          row('b', 'maybe one', RsvpServerStatus.Maybe),
          row('c', 'waitlist one', RsvpServerStatus.Waitlisted),
          row('d', 'declined one', RsvpServerStatus.CantGo),
        ],
      }),
      isPending: false,
      isError: false,
    });
    renderAt('good-token');
    expect(screen.getAllByRole('link')).toHaveLength(3);
    expect(screen.queryByRole('link', { name: /declined one/ })).not.toBeInTheDocument();
  });

  it('shows the empty state when there are no rsvps', () => {
    usePublicMyRsvps.mockReturnValue({
      data: successData({ rsvps: [] }),
      isPending: false,
      isError: false,
    });
    renderAt('good-token');
    expect(
      screen.getByText('nothing coming up 🌿 — events you rsvp to will show up here'),
    ).toBeInTheDocument();
  });

  it('shows the invalid-token empty state when the token is missing', () => {
    usePublicMyRsvps.mockReturnValue({ data: undefined, isPending: false, isError: false });
    renderAt(null);
    expect(screen.getByText(/this link's expired or invalid/)).toBeInTheDocument();
  });

  it('resends the manage link and shows the backend detail message on success', async () => {
    usePublicMyRsvps.mockReturnValue({ data: undefined, isPending: false, isError: false });
    const { rerender } = renderAt(null);

    fireEvent.click(screen.getByRole('button', { name: 'lost your link?' }));
    fireEvent.change(screen.getByLabelText('phone number'), {
      target: { value: '+14155550001' },
    });
    fireEvent.click(screen.getByRole('button', { name: 'resend my link' }));

    await waitFor(() => {
      expect(resendAsync).toHaveBeenCalledWith({ phoneNumber: '+14155550001' });
    });

    useResendPublicRsvpManageLink.mockReturnValue({
      mutateAsync: resendAsync,
      isPending: false,
      isSuccess: true,
      data: { detail: 'sent' },
    });
    rerender(
      <MemoryRouter initialEntries={['/my-rsvps']}>
        <Routes>
          <Route path="/my-rsvps" element={<PublicRsvpsScreen />} />
          <Route path="/calendar" element={<p>calendar page</p>} />
        </Routes>
      </MemoryRouter>,
    );
    expect(screen.getByText('sent')).toBeInTheDocument();
  });

  it('persists the token from the url so a later visit can reuse it', () => {
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt('good-token');
    expect(localStorage.getItem('pda-rsvp-token')).toBe('good-token');
  });

  it('restores the persisted token when the url has none', () => {
    localStorage.setItem('pda-rsvp-token', 'stored-token');
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt(null);
    expect(usePublicMyRsvps).toHaveBeenCalledWith('stored-token');
    expect(screen.getByRole('link', { name: /potluck/ })).toBeInTheDocument();
  });

  it('clears the persisted token and shows the invalid-token state on a 404', () => {
    localStorage.setItem('pda-rsvp-token', 'stale-token');
    usePublicMyRsvps.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: { isAxiosError: true, response: { status: 404 } },
    });
    renderAt(null);
    expect(screen.getByText(/this link's expired or invalid/)).toBeInTheDocument();
    expect(localStorage.getItem('pda-rsvp-token')).toBeNull();
  });

  it('shows the invalid-token empty state on a 404 (expired or revoked)', () => {
    usePublicMyRsvps.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: { isAxiosError: true, response: { status: 404 } },
    });
    renderAt('bad-token');
    expect(screen.getByText(/this link's expired or invalid/)).toBeInTheDocument();
  });

  it('shows a retry message (not the invalid-token state) on a transient error', () => {
    usePublicMyRsvps.mockReturnValue({
      data: undefined,
      isPending: false,
      isError: true,
      error: { isAxiosError: true, response: { status: 429 } },
    });
    renderAt('good-token');
    expect(screen.getByText(/couldn't load your rsvps/)).toBeInTheDocument();
    expect(screen.queryByText(/this link's expired or invalid/)).not.toBeInTheDocument();
  });

  it('clears the stored token when "not you?" is confirmed', () => {
    localStorage.setItem('pda-rsvp-token', 'good-token');
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt('good-token');

    fireEvent.click(screen.getByRole('button', { name: 'not you?' }));
    fireEvent.click(screen.getByRole('button', { name: 'forget me' }));

    expect(localStorage.getItem('pda-rsvp-token')).toBeNull();
    expect(screen.getByText('calendar page')).toBeInTheDocument();
  });

  it('keeps the stored token when "not you?" is cancelled', () => {
    localStorage.setItem('pda-rsvp-token', 'good-token');
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt('good-token');

    fireEvent.click(screen.getByRole('button', { name: 'not you?' }));
    fireEvent.click(screen.getByRole('button', { name: 'cancel' }));

    expect(localStorage.getItem('pda-rsvp-token')).toBe('good-token');
  });

  it('has no axe violations', async () => {
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    const { container } = renderAt('good-token');
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);
});
