import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

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
import {
  useHome,
  useUpdateHome,
  useGuidelines,
  useUpdateGuidelines,
} from './content';

const mockedGet = vi.mocked(apiClient.get);
const mockedPatch = vi.mocked(apiClient.patch);

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
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
        join_content: 'join delta',
        join_content_pm: '{"type":"doc"}',
        join_content_html: '<p>join</p>',
        donate_url: 'https://example.com/donate',
        updated_at: '2024-01-01T00:00:00Z',
      },
    });

    const { result } = renderHook(() => useHome(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toEqual({
      content: 'delta',
      contentPm: '{"type":"doc"}',
      contentHtml: '<p>hello</p>',
      joinContent: 'join delta',
      joinContentPm: '{"type":"doc"}',
      joinContentHtml: '<p>join</p>',
      donateUrl: 'https://example.com/donate',
      updatedAt: '2024-01-01T00:00:00Z',
    });

    expect(mockedGet).toHaveBeenCalledWith('/api/community/home/');
  });

  it('defaults donateUrl to empty string when null in response', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        content_html: '<p>hi</p>',
        updated_at: '2024-01-01T00:00:00Z',
        // donate_url omitted — wire type allows undefined
      },
    });

    const { result } = renderHook(() => useHome(), { wrapper: wrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data?.donateUrl).toBe('');
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
      donate_url: 'https://example.com/donate',
      updated_at: '2024-06-01T00:00:00Z',
    };
    mockedPatch.mockResolvedValueOnce({ data: wireResponse });

    const { result } = renderHook(() => useUpdateHome(), { wrapper: wrapper() });

    await result.current.mutateAsync({
      contentPm: '{"type":"doc"}',
      donateUrl: 'https://example.com/donate',
    });

    expect(mockedPatch).toHaveBeenCalledWith('/api/community/home/', {
      content_pm: '{"type":"doc"}',
      donate_url: 'https://example.com/donate',
    });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));
  });

  it('propagates error on API failure', async () => {
    const apiError = new Error('network error');
    mockedPatch.mockRejectedValueOnce(apiError);

    const { result } = renderHook(() => useUpdateHome(), { wrapper: wrapper() });

    await expect(result.current.mutateAsync({ contentPm: 'x' })).rejects.toThrow(
      'network error',
    );
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
