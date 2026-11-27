import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { useClubReps, useSetClubReps } from './clubs';

vi.mock('@/api/client');

const mockedGet = vi.mocked(apiClient.get);
const mockedPut = vi.mocked(apiClient.put);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useClubReps', () => {
  it('maps reps by club id', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        { club_id: 'c1', reps: [{ id: 'u1', full_name: 'Ada', phone_number: '+15551230001' }] },
        { club_id: 'c2', reps: [] },
      ],
    });
    const { result } = renderHook(() => useClubReps(), { wrapper: queryWrapper() });
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });
    expect(mockedGet).toHaveBeenCalledWith('/api/community/clubs/reps/');
    expect(result.current.data?.get('c1')).toEqual([
      { id: 'u1', fullName: 'Ada', phoneNumber: '+15551230001' },
    ]);
    expect(result.current.data?.get('c2')).toEqual([]);
  });
});

describe('useSetClubReps', () => {
  it('puts the user ids and invalidates clubs', async () => {
    mockedPut.mockResolvedValueOnce({ data: { club_id: 'c1', reps: [] } });
    const qc = makeQueryClient();
    const spy = vi.spyOn(qc, 'invalidateQueries');
    const { result } = renderHook(() => useSetClubReps('c1'), { wrapper: queryWrapper(qc) });
    await result.current.mutateAsync({ userIds: ['u1'] });
    expect(mockedPut).toHaveBeenCalledWith('/api/community/clubs/c1/reps/', { user_ids: ['u1'] });
    await waitFor(() => expect(spy).toHaveBeenCalledWith({ queryKey: ['clubs'] }));
  });
});
