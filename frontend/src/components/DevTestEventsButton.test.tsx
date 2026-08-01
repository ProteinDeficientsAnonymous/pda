import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/devTools', () => ({
  useCreateDevTestEvents: vi.fn(),
  useDeleteDevTestEvents: vi.fn(),
}));

vi.mock('@/api/version', () => ({
  useVersion: vi.fn(),
}));

vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn(),
}));

import { useCreateDevTestEvents, useDeleteDevTestEvents } from '@/api/devTools';
import { useVersion } from '@/api/version';
import { useAuthStore } from '@/auth/store';

import { DevTestEventsButton } from './DevTestEventsButton';

const mockUseVersion = vi.mocked(useVersion);
const mockUseAuthStore = vi.mocked(useAuthStore);
const mockUseCreate = vi.mocked(useCreateDevTestEvents);
const mockUseDelete = vi.mocked(useDeleteDevTestEvents);

function renderButton() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <DevTestEventsButton />
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseAuthStore.mockImplementation((selector) => selector({ status: 'authed' } as never));
  mockUseCreate.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({ events: [{ id: '1' }] }),
    isPending: false,
  } as unknown as ReturnType<typeof useCreateDevTestEvents>);
  mockUseDelete.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue(undefined),
    isPending: false,
  } as unknown as ReturnType<typeof useDeleteDevTestEvents>);
});

describe('DevTestEventsButton', () => {
  it('renders on local/staging when authed', () => {
    mockUseVersion.mockReturnValue({
      data: { commitSha: 'a', commitShaShort: 'a', environment: 'staging' },
    } as ReturnType<typeof useVersion>);
    renderButton();
    expect(screen.getByLabelText('dev test events')).toBeInTheDocument();
  });

  it('renders nothing in production', () => {
    mockUseVersion.mockReturnValue({
      data: { commitSha: 'a', commitShaShort: 'a', environment: 'production' },
    } as ReturnType<typeof useVersion>);
    renderButton();
    expect(screen.queryByLabelText('dev test events')).not.toBeInTheDocument();
  });

  it('renders nothing when not authed', () => {
    mockUseAuthStore.mockImplementation((selector) => selector({ status: 'anon' } as never));
    mockUseVersion.mockReturnValue({
      data: { commitSha: 'a', commitShaShort: 'a', environment: 'staging' },
    } as ReturnType<typeof useVersion>);
    renderButton();
    expect(screen.queryByLabelText('dev test events')).not.toBeInTheDocument();
  });

  it('creates events with the chosen count', async () => {
    const user = userEvent.setup();
    mockUseVersion.mockReturnValue({
      data: { commitSha: 'a', commitShaShort: 'a', environment: 'local' },
    } as ReturnType<typeof useVersion>);
    const mutateAsync = vi.fn().mockResolvedValue({ events: [{ id: '1' }] });
    mockUseCreate.mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateDevTestEvents>);

    renderButton();
    await user.click(screen.getByLabelText('dev test events'));
    await user.click(screen.getByRole('button', { name: 'create' }));

    expect(mutateAsync).toHaveBeenCalledWith(1);
  });
});
