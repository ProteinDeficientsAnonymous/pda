import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook, waitFor } from '@testing-library/react';
import type { ReactNode } from 'react';
import { createElement } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn() },
}));

// useGuidelines gates on auth status — mock the store before importing hooks
vi.mock('@/auth/store', () => ({
  useAuthStore: vi.fn((selector: (s: { status: string }) => unknown) =>
    selector({ status: 'authed' }),
  ),
}));

import { apiClient } from '@/api/client';

import { useGuidelines, useHome, useUpdateGuidelines, useUpdateHome } from './content';

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

// ---------------------------------------------------------------------------
// useHome
// ---------------------------------------------------------------------------

describe('useHome', () => {
  it('returns mapped home page data on success', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        content: 'delta',
        content_pm: '{"type":"doc"}',
        content_html: '<p>hello</p>',
        updated_at: '2024-01-01T00:00:00Z',
      },
    });

    const { result } = renderHook(() => useHome(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      content: 'delta',
      contentPm: '{"type":"doc"}',
      contentHtml: '<p>hello</p>',
      updatedAt: '2024-01-01T00:00:00Z',
    });

    expect(mockedGet).toHaveBeenCalledWith('/api/community/home/');
  });

  it('defaults missing string fields to empty string', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        content_html: '<p>hi</p>',
        updated_at: '2024-01-01T00:00:00Z',
      },
    });

    const { result } = renderHook(() => useHome(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.content).toBe('');
    expect(result.current.data?.contentPm).toBe('');
  });
});

// ---------------------------------------------------------------------------
// useUpdateHome
// ---------------------------------------------------------------------------

describe('useUpdateHome', () => {
  it('PATCHes home and sets query data on success', async () => {
    const wireResponse = {
      content_pm: '{"type":"doc"}',
      content_html: '<p>updated</p>',
      updated_at: '2024-06-01T00:00:00Z',
    };
    mockedPatch.mockResolvedValueOnce({ data: wireResponse });

    const { result } = renderHook(() => useUpdateHome(), { wrapper: wrapper() });

    await result.current.mutateAsync({
      contentPm: '{"type":"doc"}',
    });

    expect(mockedPatch).toHaveBeenCalledWith('/api/community/home/', {
      content_pm: '{"type":"doc"}',
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('propagates error on API failure', async () => {
    const apiError = new Error('network error');
    mockedPatch.mockRejectedValueOnce(apiError);

    const { result } = renderHook(() => useUpdateHome(), { wrapper: wrapper() });

    await expect(result.current.mutateAsync({ contentPm: 'x' })).rejects.toThrow('network error');
    await waitFor(() => expect(result.current.isError).toBe(true));
  });
});

// ---------------------------------------------------------------------------
// useGuidelines
// ---------------------------------------------------------------------------

describe('useGuidelines', () => {
  it('returns mapped guidelines content on success', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        content: 'guidelines delta',
        content_pm: '{"type":"doc"}',
        content_html: '<p>guidelines</p>',
        updated_at: '2024-03-01T00:00:00Z',
      },
    });

    const { result } = renderHook(() => useGuidelines(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      content: 'guidelines delta',
      contentPm: '{"type":"doc"}',
      contentHtml: '<p>guidelines</p>',
      updatedAt: '2024-03-01T00:00:00Z',
    });

    expect(mockedGet).toHaveBeenCalledWith('/api/community/guidelines/');
  });

  it('propagates error on API failure', async () => {
    const apiError = new Error('server error');
    mockedGet.mockRejectedValueOnce(apiError);

    const { result } = renderHook(() => useGuidelines(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.error).toBe(apiError);
  });
});

// ---------------------------------------------------------------------------
// useUpdateGuidelines
// ---------------------------------------------------------------------------

describe('useUpdateGuidelines', () => {
  it('PATCHes guidelines and invalidates guidelines query', async () => {
    mockedPatch.mockResolvedValueOnce({
      data: {
        content_html: '<p>new</p>',
        updated_at: '2024-06-01T00:00:00Z',
      },
    });

    const { result } = renderHook(() => useUpdateGuidelines(), { wrapper: wrapper() });

    await result.current.mutateAsync('{"type":"doc","content":[]}');

    expect(mockedPatch).toHaveBeenCalledWith('/api/community/guidelines/', {
      content_pm: '{"type":"doc","content":[]}',
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });
});
