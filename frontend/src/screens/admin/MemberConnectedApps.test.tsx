import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  type ConnectedApp,
  useMemberConnectedApps,
  useRevokeMemberConnectedApp,
} from '@/api/connect';
import { useAuthStore } from '@/auth/store';
import { makeUser } from '@/test/fixtures';

import { MemberConnectedApps } from './MemberConnectedApps';

vi.mock('@/api/connect', () => ({
  useMemberConnectedApps: vi.fn(),
  useRevokeMemberConnectedApp: vi.fn(),
}));

const revoke = vi.fn<(id: string) => Promise<void>>();

const claude: ConnectedApp = {
  id: 'grant-1',
  clientName: 'Claude',
  createdAt: new Date('2026-03-04T12:00:00Z'),
  lastUsedAt: null,
};

function setViewer(permissions: string[]) {
  useAuthStore.setState({
    status: 'authed',
    user: makeUser({ roles: [{ id: 'r1', name: 'vetter', isDefault: false, permissions }] }),
  });
}

describe('MemberConnectedApps', () => {
  beforeEach(() => {
    revoke.mockReset();
    revoke.mockResolvedValue(undefined);
    vi.mocked(useMemberConnectedApps).mockReturnValue({
      data: [claude],
      isPending: false,
      isError: false,
    } as unknown as ReturnType<typeof useMemberConnectedApps>);
    vi.mocked(useRevokeMemberConnectedApp).mockReturnValue({
      mutateAsync: revoke,
      isPending: false,
    } as unknown as ReturnType<typeof useRevokeMemberConnectedApp>);
  });

  afterEach(() => {
    useAuthStore.setState({ status: 'idle', user: null, accessToken: null });
  });

  it('hidden without manage_users', () => {
    setViewer(['approve_join_requests']);
    render(<MemberConnectedApps memberId="member-1" />);
    expect(screen.queryByText('connected apps')).not.toBeInTheDocument();
    expect(useMemberConnectedApps).not.toHaveBeenCalled();
  });

  it('lists the member apps and revokes for that member after confirm', async () => {
    setViewer(['manage_users']);
    render(<MemberConnectedApps memberId="member-1" />);
    expect(screen.getByRole('heading', { name: 'connected apps' })).toBeInTheDocument();
    expect(useMemberConnectedApps).toHaveBeenCalledWith('member-1');
    expect(useRevokeMemberConnectedApp).toHaveBeenCalledWith('member-1');
    expect(screen.getByText('last used never')).toBeInTheDocument();
    await userEvent.click(screen.getByRole('button', { name: 'disconnect' }));
    await userEvent.click(screen.getAllByRole('button', { name: 'disconnect' })[1]!);
    await waitFor(() => {
      expect(revoke).toHaveBeenCalledWith('grant-1');
    });
  });
});
