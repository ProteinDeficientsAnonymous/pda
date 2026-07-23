import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

import { apiClient } from '@/api/client';
import { Feature } from '@/models/featureFlags';

import { useFeatureFlags, useFlag, useSetFeatureFlag } from './featureFlags';

const mockedGet = vi.mocked(apiClient.get);
const mockedPatch = vi.mocked(apiClient.patch);

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: ReactNode }) =>
    createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useFeatureFlags', () => {
  it('returns the resolved flags map on success', async () => {
    mockedGet.mockResolvedValueOnce({ data: { flags: { host_attendance_report: true } } });

    const { result } = renderHook(() => useFeatureFlags(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(result.current.data).toEqual({ host_attendance_report: true });
    expect(mockedGet).toHaveBeenCalledWith('/api/community/feature-flags/');
  });
});

describe('useFlag', () => {
  it('returns the resolved boolean when the flag is on', async () => {
    mockedGet.mockResolvedValueOnce({ data: { flags: { host_attendance_report: true } } });

    const { result } = renderHook(() => useFlag(Feature.HostAttendanceReport), {
      wrapper: wrapper(),
    });

    await waitFor(() => expect(result.current).toBe(true));
  });

  it('fail-closes to false while loading', () => {
    mockedGet.mockReturnValueOnce(new Promise(() => {}));

    const { result } = renderHook(() => useFlag(Feature.HostAttendanceReport), {
      wrapper: wrapper(),
    });

    expect(result.current).toBe(false);
  });

  it('fail-closes to false when the key is absent from the resolved map', async () => {
    mockedGet.mockResolvedValueOnce({ data: { flags: {} } });

    const { result } = renderHook(() => useFlag(Feature.HostAttendanceReport), {
      wrapper: wrapper(),
    });

    // let the query settle, then confirm it stays closed
    await waitFor(() => expect(mockedGet).toHaveBeenCalled());
    expect(result.current).toBe(false);
  });
});

describe('useSetFeatureFlag', () => {
  it('patches the flag and returns the resolved map', async () => {
    mockedPatch.mockResolvedValueOnce({ data: { flags: { host_attendance_report: true } } });

    const { result } = renderHook(() => useSetFeatureFlag(), { wrapper: wrapper() });

    const flags = await result.current.mutateAsync({
      key: Feature.HostAttendanceReport,
      enabled: true,
    });

    expect(mockedPatch).toHaveBeenCalledWith(
      '/api/community/feature-flags/host_attendance_report/',
      {
        enabled: true,
      },
    );
    expect(flags).toEqual({ host_attendance_report: true });
  });

  it('writes the resolved map straight into the flags cache without a refetch', async () => {
    mockedPatch.mockResolvedValueOnce({ data: { flags: { host_attendance_report: true } } });
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const wrap = ({ children }: { children: ReactNode }) =>
      createElement(QueryClientProvider, { client: qc }, children);

    const { result } = renderHook(() => useSetFeatureFlag(), { wrapper: wrap });
    await result.current.mutateAsync({ key: Feature.HostAttendanceReport, enabled: true });

    expect(qc.getQueryData(['feature-flags'])).toEqual({ host_attendance_report: true });
    expect(mockedGet).not.toHaveBeenCalled();
  });
});
