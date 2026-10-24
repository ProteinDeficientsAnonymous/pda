import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { type ConnectedApp, useConnectedApps, useRevokeConnectedApp } from '@/api/connect';

import { ConnectedAppsSection } from './ConnectedAppsSection';

vi.mock('@/api/connect', () => ({
  useConnectedApps: vi.fn(),
  useRevokeConnectedApp: vi.fn(),
}));

const revoke = vi.fn<(id: string) => Promise<void>>();

const claude: ConnectedApp = {
  id: 'grant-1',
  clientName: 'Claude',
  createdAt: new Date('2026-03-04T12:00:00Z'),
  lastUsedAt: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000),
};
const neverUsed: ConnectedApp = {
  id: 'grant-2',
  clientName: 'Other App',
  createdAt: new Date('2026-04-05T12:00:00Z'),
  lastUsedAt: null,
};

function mockApps(apps: ConnectedApp[], state: { isPending?: boolean; isError?: boolean } = {}) {
  vi.mocked(useConnectedApps).mockReturnValue({
    data: state.isPending || state.isError ? undefined : apps,
    isPending: state.isPending ?? false,
    isError: state.isError ?? false,
  } as unknown as ReturnType<typeof useConnectedApps>);
  vi.mocked(useRevokeConnectedApp).mockReturnValue({
    mutateAsync: revoke,
    isPending: false,
  } as unknown as ReturnType<typeof useRevokeConnectedApp>);
}

describe('ConnectedAppsSection', () => {
  beforeEach(() => {
    revoke.mockReset();
    revoke.mockResolvedValue(undefined);
  });

  it('lists connected apps', () => {
    mockApps([claude, neverUsed]);
    render(<ConnectedAppsSection />);
    expect(screen.getByText('Claude')).toBeInTheDocument();
    expect(screen.getByText('connected mar 4, 2026')).toBeInTheDocument();
    expect(screen.getByText('last used 3 days ago')).toBeInTheDocument();
    expect(screen.getByText('Other App')).toBeInTheDocument();
    expect(screen.getByText('last used never')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    mockApps([]);
    render(<ConnectedAppsSection />);
    expect(
      screen.getByText('no apps connected. add pda as a connector in your ai app to connect one.'),
    ).toBeInTheDocument();
  });

  it('shows loading and error states', () => {
    mockApps([], { isPending: true });
    const { rerender } = render(<ConnectedAppsSection />);
    expect(screen.getByText('loading connected apps…')).toBeInTheDocument();
    mockApps([], { isError: true });
    rerender(<ConnectedAppsSection />);
    expect(screen.getByText("couldn't load connected apps")).toBeInTheDocument();
  });

  it('disconnect calls revoke after confirm', async () => {
    mockApps([claude]);
    render(<ConnectedAppsSection />);
    await userEvent.click(screen.getByRole('button', { name: 'disconnect' }));
    expect(
      screen.getByText('disconnect Claude? it will lose access right away.'),
    ).toBeInTheDocument();
    expect(revoke).not.toHaveBeenCalled();
    await userEvent.click(screen.getAllByRole('button', { name: 'disconnect' })[1]!);
    await waitFor(() => {
      expect(revoke).toHaveBeenCalledWith('grant-1');
    });
  });

  it('does not revoke when the confirm is cancelled', async () => {
    mockApps([claude]);
    render(<ConnectedAppsSection />);
    await userEvent.click(screen.getByRole('button', { name: 'disconnect' }));
    await userEvent.click(screen.getByRole('button', { name: 'cancel' }));
    expect(revoke).not.toHaveBeenCalled();
  });

  it('disables disconnect while a revoke is in flight', async () => {
    revoke.mockReturnValue(new Promise(() => undefined));
    mockApps([claude, neverUsed]);
    render(<ConnectedAppsSection />);
    await userEvent.click(screen.getAllByRole('button', { name: 'disconnect' })[0]!);
    await userEvent.click(screen.getAllByRole('button', { name: 'disconnect' })[2]!);
    const busy = await screen.findByRole('button', { name: 'disconnecting…' });
    expect(busy).toBeDisabled();
    expect(screen.getByRole('button', { name: 'disconnect' })).toBeDisabled();
    expect(revoke).toHaveBeenCalledTimes(1);
  });
});
