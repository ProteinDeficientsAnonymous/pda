import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';

import {
  useChecklist,
  useCreateChecklistItem,
  useDeleteChecklistItem,
  useMoveChecklistItem,
  useUpdateChecklistItem,
} from './planningChecklist';

vi.mock('@/api/client');

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useChecklist', () => {
  it('loads the shared checklist', async () => {
    const items = [{ id: 'i1', text: 'secure venue', detail: '' }];
    vi.mocked(apiClient.get).mockResolvedValue({ data: items });
    const { result } = renderHook(useChecklist, { wrapper: queryWrapper() });
    await waitFor(() => {
      expect(result.current.data).toEqual(items);
    });
    expect(apiClient.get).toHaveBeenCalledWith('/api/community/planning/checklist/');
  });
});

describe('checklist mutations', () => {
  it('create posts the item and refreshes planning queries', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: null });
    const qc = makeQueryClient();
    const invalidate = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(useCreateChecklistItem, { wrapper: queryWrapper(qc) });
    await result.current.mutateAsync({ text: 'book the room', detail: '' });
    expect(apiClient.post).toHaveBeenCalledWith('/api/community/planning/checklist/', {
      text: 'book the room',
      detail: '',
    });
    expect(invalidate).toHaveBeenCalledWith({ queryKey: ['planning'] });
  });

  it('update patches the item', async () => {
    vi.mocked(apiClient.patch).mockResolvedValue({ data: null });
    const { result } = renderHook(useUpdateChecklistItem, { wrapper: queryWrapper() });
    await result.current.mutateAsync({ id: 'i1', input: { text: 'secure a venue', detail: '' } });
    expect(apiClient.patch).toHaveBeenCalledWith('/api/community/planning/checklist/i1/', {
      text: 'secure a venue',
      detail: '',
    });
  });

  it('delete removes the item', async () => {
    vi.mocked(apiClient.delete).mockResolvedValue({ data: null });
    const { result } = renderHook(useDeleteChecklistItem, { wrapper: queryWrapper() });
    await result.current.mutateAsync('i1');
    expect(apiClient.delete).toHaveBeenCalledWith('/api/community/planning/checklist/i1/');
  });

  it('move posts the direction', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: [] });
    const { result } = renderHook(useMoveChecklistItem, { wrapper: queryWrapper() });
    await result.current.mutateAsync({ id: 'i2', direction: 'up' });
    expect(apiClient.post).toHaveBeenCalledWith('/api/community/planning/checklist/i2/move/', {
      direction: 'up',
    });
  });
});
