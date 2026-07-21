import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { axe } from 'vitest-axe';

import type { ManageRsvps } from '@/api/publicRsvp';
import { RsvpServerStatus, RsvpStatus } from '@/models/event';
import { makeEvent } from '@/test/fixtures';

const toastSuccess = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    success: (m: string) => {
      toastSuccess(m);
    },
    error: vi.fn(),
  },
}));

const updateAsync = vi.fn();
const cancelAsync = vi.fn();
const resendAsync = vi.fn();
const usePublicMyRsvps = vi.fn();
const useResendPublicRsvpManageLink = vi.fn();

vi.mock('@/api/publicRsvp', () => ({
  usePublicMyRsvps: (token: string) => usePublicMyRsvps(token) as unknown,
  useUpdatePublicMyRsvp: () => ({ mutateAsync: updateAsync, isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: cancelAsync, isPending: false }),
  useResendPublicRsvpManageLink: () => useResendPublicRsvpManageLink() as unknown,
}));

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

import PublicRsvpsScreen from './PublicRsvpsScreen';

function renderAt(token: string | null) {
  const path = token === null ? '/my-rsvps' : `/my-rsvps?token=${token}`;
  return render(
    <MemoryRouter initialEntries={[path]}>
      <PublicRsvpsScreen />
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
  updateAsync.mockResolvedValue({});
  cancelAsync.mockResolvedValue(undefined);
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
    expect(screen.getByRole('heading', { name: 'your rsvps' })).toBeInTheDocument();
    expect(screen.getByText('sam green')).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: 'potluck' })).toBeInTheDocument();
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
        <PublicRsvpsScreen />
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
    expect(screen.getByRole('heading', { name: 'your rsvps' })).toBeInTheDocument();
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

  it('posts to the manage endpoint and shows the update toast when editing status', async () => {
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt('good-token');

    fireEvent.click(screen.getByRole('button', { name: 'maybe' }));

    await waitFor(() => {
      expect(updateAsync).toHaveBeenCalledWith({
        eventId: 'ev1',
        status: RsvpStatus.Maybe,
        hasPlusOne: false,
      });
    });
    expect(toastSuccess).toHaveBeenCalledWith(
      'rsvp updated — check your email for an updated link',
    );
  });

  it('cancels the rsvp via the delete endpoint', async () => {
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt('good-token');

    fireEvent.click(screen.getByRole('button', { name: 'cancel rsvp' }));

    await waitFor(() => {
      expect(cancelAsync).toHaveBeenCalledWith('ev1');
    });
  });

  it('clears the stored token when "not you?" is confirmed', () => {
    localStorage.setItem('pda-rsvp-token', 'good-token');
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    renderAt('good-token');

    fireEvent.click(screen.getByRole('button', { name: 'not you?' }));
    fireEvent.click(screen.getByRole('button', { name: 'forget me' }));

    expect(localStorage.getItem('pda-rsvp-token')).toBeNull();
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
