import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { makeQueryClient, queryWrapper } from '@/test/render';

import { useCheckInReport } from './eventCheckInReport';

vi.mock('@/api/client');

const mockedGet = vi.mocked(apiClient.get);

const wirePerson = (id: string) => ({
  user_id: id,
  name: id,
  phone: null,
  is_member: true,
  is_plus_one_guest: false,
});

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useCheckInReport', () => {
  it('maps unmarked going and not-going guests into separate lists', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        attended_count: 0,
        no_show_count: 0,
        canceled_count: 0,
        unmarked_going_count: 1,
        unmarked_not_going_count: 1,
        attended: [],
        no_shows: [],
        canceled: [],
        unmarked_going: [wirePerson('going')],
        unmarked_not_going: [wirePerson('maybe')],
      },
    });
    const qc = makeQueryClient();
    const { result } = renderHook(() => useCheckInReport('ev1'), { wrapper: queryWrapper(qc) });
    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedGet).toHaveBeenCalledWith('/api/community/events/ev1/report/');
    expect(result.current.data?.unmarkedGoingCount).toBe(1);
    expect(result.current.data?.unmarkedNotGoingCount).toBe(1);
    expect(result.current.data?.unmarkedGoing.map((p) => p.userId)).toEqual(['going']);
    expect(result.current.data?.unmarkedNotGoing.map((p) => p.userId)).toEqual(['maybe']);
  });
});
