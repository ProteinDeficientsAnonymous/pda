import React from 'react';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';

vi.mock('@/api/client', () => ({
  apiClient: { get: vi.fn(), post: vi.fn(), patch: vi.fn(), delete: vi.fn(), put: vi.fn() },
  authClient: { post: vi.fn() },
  setAuthBridge: vi.fn(),
}));

import { apiClient } from '@/api/client';
import {
  useCreateDocFolder,
  useCreateDocument,
  useDeleteDocFolder,
  useDeleteDocument,
  useReorderDocFolders,
  useReorderDocuments,
} from './docs';

const mockedPost = vi.mocked(apiClient.post);
const mockedDelete = vi.mocked(apiClient.delete);
const mockedPut = vi.mocked(apiClient.put);

function makeQc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function makeWrapper(qc: QueryClient) {
  return ({ children }: { children: React.ReactNode }) =>
    React.createElement(QueryClientProvider, { client: qc }, children);
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useCreateDocFolder', () => {
  it('should post folder and invalidate tree', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'f1',
        name: 'guides',
        parent_id: null,
        display_order: 0,
        children: [],
        documents: [],
      },
    });
    const qc = makeQc();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useCreateDocFolder(), { wrapper: makeWrapper(qc) });
    await result.current.mutateAsync({ name: 'guides', parentId: null });
    expect(mockedPost).toHaveBeenCalledWith('/api/community/docs/folders/', {
      name: 'guides',
      parent_id: null,
    });
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['docs', 'folders'] }));
  });
});

describe('useCreateDocument', () => {
  it('should post document', async () => {
    mockedPost.mockResolvedValueOnce({
      data: {
        id: 'd1',
        title: 'welcome',
        content: '',
        content_pm: '',
        content_html: '<p></p>',
        folder_id: 'f1',
        display_order: 0,
        created_by_id: 'u1',
        created_at: '2026-01-01T00:00:00Z',
        updated_at: '2026-01-01T00:00:00Z',
      },
    });
    const qc = makeQc();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useCreateDocument(), { wrapper: makeWrapper(qc) });
    await result.current.mutateAsync({ title: 'welcome', folderId: 'f1' });
    expect(mockedPost).toHaveBeenCalledWith('/api/community/docs/', {
      title: 'welcome',
      folder_id: 'f1',
      content: '',
      content_pm: '',
    });
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['docs', 'folders'] }));
  });
});

describe('useDeleteDocument', () => {
  it('should delete by id', async () => {
    mockedDelete.mockResolvedValueOnce({ data: { detail: 'ok' } });
    const qc = makeQc();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteDocument(), { wrapper: makeWrapper(qc) });
    await result.current.mutateAsync('d9');
    expect(mockedDelete).toHaveBeenCalledWith('/api/community/docs/d9/');
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['docs', 'folders'] }));
  });
});

describe('useDeleteDocFolder', () => {
  it('should delete folder', async () => {
    mockedDelete.mockResolvedValueOnce({ data: { detail: 'ok' } });
    const qc = makeQc();
    const { result } = renderHook(() => useDeleteDocFolder(), { wrapper: makeWrapper(qc) });
    await result.current.mutateAsync('f9');
    expect(mockedDelete).toHaveBeenCalledWith('/api/community/docs/folders/f9/');
  });
});

describe('useReorderDocuments', () => {
  it('should put document order', async () => {
    mockedPut.mockResolvedValueOnce({ data: { detail: 'ok' } });
    const qc = makeQc();
    const { result } = renderHook(() => useReorderDocuments(), { wrapper: makeWrapper(qc) });
    await result.current.mutateAsync(['d2', 'd1']);
    expect(mockedPut).toHaveBeenCalledWith('/api/community/docs/reorder/', { ids: ['d2', 'd1'] });
  });
});

describe('useReorderDocFolders', () => {
  it('should put folder order', async () => {
    mockedPut.mockResolvedValueOnce({ data: { detail: 'ok' } });
    const qc = makeQc();
    const { result } = renderHook(() => useReorderDocFolders(), { wrapper: makeWrapper(qc) });
    await result.current.mutateAsync(['b', 'a']);
    expect(mockedPut).toHaveBeenCalledWith('/api/community/docs/folders/reorder/', {
      ids: ['b', 'a'],
    });
  });
});
