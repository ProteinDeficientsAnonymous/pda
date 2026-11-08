import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { expect, it, vi } from 'vitest';

import type * as JoinApi from '@/api/join';
import { useRestoredMembers } from '@/api/restoredMembers';
import { renderWithProviders } from '@/test/render';

import JoinRequestsScreen from './JoinRequestsScreen';

vi.mock('@/api/join', async (importOriginal) => ({
  ...(await importOriginal<typeof JoinApi>()),
  useJoinRequests: vi.fn(() => ({ data: [], isPending: false, isError: false })),
  useDecideJoinRequest: vi.fn(() => ({ isPending: false })),
  useUnrejectJoinRequest: vi.fn(() => ({ isPending: false })),
  useResendMagicLink: vi.fn(() => ({ isPending: false })),
}));
vi.mock('@/api/restoredMembers', () => ({ useRestoredMembers: vi.fn() }));
vi.mock('@/api/users', () => ({ useUpdateUser: vi.fn(() => ({ isPending: false })) }));
vi.mock('./JoinRequestMessageEditors', () => ({ JoinRequestMessageEditors: () => null }));

it('shows restored members and their hint on the restored tab', async () => {
  vi.mocked(useRestoredMembers).mockReturnValue({
    data: [
      {
        id: 'u1',
        full_name: 'Ada Lovelace',
        phone_number: '+16505550001',
        restored_at: '2026-03-04T12:00:00Z',
        has_joined_whatsapp: false,
        recent_events: [],
      },
    ],
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useRestoredMembers>);
  renderWithProviders(<JoinRequestsScreen />);

  await userEvent.click(screen.getByRole('radio', { name: 'restored' }));

  expect(screen.getByText('Ada Lovelace')).toBeInTheDocument();
  expect(screen.getByText(/restored members stay here until/)).toBeInTheDocument();
  expect(screen.getByPlaceholderText('name or phone')).toBeInTheDocument();
  expect(screen.queryByText('nothing here 🌿')).not.toBeInTheDocument();
});
