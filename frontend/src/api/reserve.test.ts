import { describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import { fetchReserve } from './reserve';

vi.mock('@/api/client');

describe('fetchReserve', () => {
  it('fetches and maps entries to numbers', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        entries: [
          {
            id: 'r1',
            label: 'stickers',
            occurred_on: '2026-11-15',
            collected: '0.00',
            paid_out: '103.65',
            facilitator_drinks: '0.00',
            left_over: '-103.65',
          },
        ],
        updated_at: '2026-11-15T20:00:00Z',
      },
    });

    const reserve = await fetchReserve();

    expect(apiClient.get).toHaveBeenCalledWith('/api/community/reserve/');
    expect(reserve.updatedAt).toEqual(new Date('2026-11-15T20:00:00Z'));
    expect(reserve.entries).toEqual([
      {
        id: 'r1',
        label: 'stickers',
        collected: 0,
        paidOut: 103.65,
        facilitatorDrinks: 0,
        leftOver: -103.65,
      },
    ]);
  });

  it('keeps updatedAt null when there are no entries', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { entries: [], updated_at: null } });

    expect(await fetchReserve()).toEqual({ entries: [], updatedAt: null });
  });
});
