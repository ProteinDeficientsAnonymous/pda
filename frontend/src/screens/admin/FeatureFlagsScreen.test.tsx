import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/featureFlags', () => ({
  useFeatureFlags: vi.fn(),
  useSetFeatureFlag: vi.fn(),
}));

vi.mock('@/api/version', () => ({
  useVersion: vi.fn(),
}));

import { useFeatureFlags, useSetFeatureFlag } from '@/api/featureFlags';
import { useVersion } from '@/api/version';

import FeatureFlagsScreen from './FeatureFlagsScreen';

const mockUseFlags = vi.mocked(useFeatureFlags);
const mockUseSetFlag = vi.mocked(useSetFeatureFlag);
const mockUseVersion = vi.mocked(useVersion);
const mockMutate = vi.fn();

function mockFlagsResult(overrides: Partial<ReturnType<typeof useFeatureFlags>>) {
  mockUseFlags.mockReturnValue({
    isPending: false,
    isError: false,
    data: { example_flag: false },
    ...overrides,
  } as ReturnType<typeof useFeatureFlags>);
}

function renderScreen() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <FeatureFlagsScreen />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  mockUseVersion.mockReturnValue({
    data: { commitSha: 'abc', commitShaShort: 'abc', environment: 'staging' },
  } as ReturnType<typeof useVersion>);
  mockUseSetFlag.mockReturnValue({
    mutate: mockMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useSetFeatureFlag>);
});

describe('FeatureFlagsScreen', () => {
  it('renders a toggle per flag and calls the mutation on change', async () => {
    mockFlagsResult({ data: { example_flag: false } });

    renderScreen();

    const toggle = screen.getByRole('switch', { name: /example flag/i });
    expect(toggle).toHaveAttribute('aria-checked', 'false');

    await userEvent.click(toggle);

    expect(mockMutate).toHaveBeenCalledWith({ key: 'example_flag', enabled: true });
  });

  it('shows the current environment', () => {
    mockFlagsResult({});

    renderScreen();

    expect(screen.getByText(/environment: staging/i)).toBeInTheDocument();
  });

  it('shows a loading state while pending', () => {
    mockFlagsResult({ isPending: true, data: undefined });

    renderScreen();

    expect(screen.getByText('loading…')).toBeInTheDocument();
  });

  it('shows an error message when the query fails', () => {
    mockFlagsResult({ isError: true, data: undefined });

    renderScreen();

    expect(screen.getByRole('alert')).toHaveTextContent(/couldn't load feature flags/i);
  });
});
