import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { useCreateClub, useUpdateClub } from './clubs';

vi.mock('@/api/client');

const mockedPost = vi.mocked(apiClient.post);
const mockedPatch = vi.mocked(apiClient.patch);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useCreateClub', () => {
  it('posts the club, maps the response, and invalidates the club list', async () => {
    mockedPost.mockResolvedValueOnce({
      data: { id: 'c1', name: 'chess club', requirements: 'any level' },
    });
    const qc = makeQueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useCreateClub(), { wrapper: queryWrapper(qc) });
    const club = await result.current.mutateAsync({
      name: 'chess club',
      requirements: 'any level',
    });
    expect(mockedPost).toHaveBeenCalledWith('/api/community/clubs/', {
      name: 'chess club',
      requirements: 'any level',
    });
    expect(club).toEqual({ id: 'c1', name: 'chess club', requirements: 'any level' });
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['clubs'] }));
  });
});

describe('useUpdateClub', () => {
  it('patches the club, maps the response, and invalidates the club list', async () => {
    mockedPatch.mockResolvedValueOnce({
      data: { id: 'c1', name: 'reading club', requirements: '' },
    });
    const qc = makeQueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useUpdateClub('c1'), { wrapper: queryWrapper(qc) });
    const club = await result.current.mutateAsync({ name: 'reading club', requirements: '' });
    expect(mockedPatch).toHaveBeenCalledWith('/api/community/clubs/c1/', {
      name: 'reading club',
      requirements: '',
    });
    expect(club).toEqual({ id: 'c1', name: 'reading club', requirements: '' });
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['clubs'] }));
  });
});
