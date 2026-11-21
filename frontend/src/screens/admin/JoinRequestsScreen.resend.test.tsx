import { screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as JoinApi from '@/api/join';
import {
  JoinRequestStatus,
  type JoinRequestSummary,
  useJoinRequests,
  useResendMagicLink,
} from '@/api/join';
import { makeRequest } from '@/test/fixtures';
import { renderWithProviders } from '@/test/render';

import JoinRequestsScreen from './JoinRequestsScreen';

vi.mock('@/api/join', async (importOriginal) => {
  const actual = await importOriginal<typeof JoinApi>();
  return {
    ...actual,
    useJoinRequests: vi.fn(),
    useDecideJoinRequest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
    useUnrejectJoinRequest: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
    useResendMagicLink: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  };
});

vi.mock('@/api/users', () => ({
  useUpdateUser: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}));

vi.mock('@/api/content', () => ({
  useWelcomeTemplate: () => ({ data: undefined, isPending: false, isError: false }),
  useUpdateWelcomeTemplate: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useTentativeApprovalMessage: () => ({ data: undefined, isPending: false, isError: false }),
  useUpdateTentativeApprovalMessage: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useMemberPromotionMessage: () => ({ data: undefined, isPending: false, isError: false }),
  useUpdateMemberPromotionMessage: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useMemberPromotionEmail: () => ({ data: undefined, isPending: false, isError: false }),
  useUpdateMemberPromotionEmail: () => ({ mutateAsync: vi.fn(), isPending: false }),
  useWhatsAppLink: () => ({ data: undefined, isPending: false, isError: false }),
}));

function mockResult(data: JoinRequestSummary[]) {
  vi.mocked(useJoinRequests).mockReturnValue({
    isPending: false,
    isError: false,
    data,
  } as ReturnType<typeof useJoinRequests>);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('JoinRequestsScreen re-send welcome', () => {
  it('reopens the tentative message with a fresh link for a tentative request', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({
      fullName: 'Ada Lovelace',
      firstName: 'Ada',
      phoneNumber: '+16505550001',
      status: JoinRequestStatus.TENTATIVE,
      magicLinkToken: 'fresh-tok',
    });
    vi.mocked(useResendMagicLink).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useResendMagicLink>);
    mockResult([
      makeRequest({ id: 'jr-tentative', status: JoinRequestStatus.TENTATIVE, onboardedAt: null }),
    ]);

    renderWithProviders(<JoinRequestsScreen />);
    await userEvent.click(screen.getByRole('radio', { name: 'tentative' }));
    await userEvent.click(screen.getByRole('button', { name: 're-send welcome' }));
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 're-send' }),
    );

    expect(mutateAsync).toHaveBeenCalledWith('jr-tentative');
    expect(await screen.findByText(/know they're tentatively in/)).toBeInTheDocument();
    expect(screen.getByText(/magic-login\/fresh-tok/)).toBeInTheDocument();
  });

  it('opens the approval credentials for an approved request', async () => {
    vi.mocked(useResendMagicLink).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({
        fullName: 'Ada Lovelace',
        firstName: 'Ada',
        phoneNumber: '+16505550001',
        status: JoinRequestStatus.APPROVED,
        magicLinkToken: 'fresh-tok',
      }),
      isPending: false,
    } as unknown as ReturnType<typeof useResendMagicLink>);
    mockResult([
      makeRequest({ id: 'jr-approved', status: JoinRequestStatus.APPROVED, onboardedAt: null }),
    ]);

    renderWithProviders(<JoinRequestsScreen />);
    await userEvent.click(screen.getByRole('radio', { name: 'approved' }));
    await userEvent.click(screen.getByRole('button', { name: 're-send welcome' }));
    await userEvent.click(
      within(screen.getByRole('dialog')).getByRole('button', { name: 're-send' }),
    );

    expect(await screen.findByText(/share this one-time login link/)).toBeInTheDocument();
    expect(screen.queryByText(/know they're tentatively in/)).not.toBeInTheDocument();
  });
});
