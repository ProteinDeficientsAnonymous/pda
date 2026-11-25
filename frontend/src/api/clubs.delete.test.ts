import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { useDeleteClub } from './clubs';

vi.mock('@/api/client');

const mockedDelete = vi.mocked(apiClient.delete);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useDeleteClub', () => {
  it('deletes the club and invalidates the club list', async () => {
    mockedDelete.mockResolvedValueOnce({ data: null });
    const qc = makeQueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useDeleteClub(), { wrapper: queryWrapper(qc) });
    await result.current.mutateAsync('c1');
    expect(mockedDelete).toHaveBeenCalledWith('/api/community/clubs/c1/');
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['clubs'] }));
  });
});
