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
const usePublicMyRsvps = vi.fn();

vi.mock('@/api/publicRsvp', () => ({
  usePublicMyRsvps: (token: string) => usePublicMyRsvps(token) as unknown,
  useUpdatePublicMyRsvp: () => ({ mutateAsync: updateAsync, isPending: false }),
  useCancelPublicMyRsvp: () => ({ mutateAsync: cancelAsync, isPending: false }),
}));

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
  updateAsync.mockResolvedValue({});
  cancelAsync.mockResolvedValue(undefined);
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

  it('has no axe violations', async () => {
    usePublicMyRsvps.mockReturnValue({ data: successData(), isPending: false, isError: false });
    const { container } = renderAt('good-token');
    const results = await axe(container, { rules: { 'color-contrast': { enabled: false } } });
    expect(results).toHaveNoViolations();
  }, 15000);
});
