import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { useRestoredMembers } from './restoredMembers';

vi.mock('@/api/client');

const mockedGet = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useRestoredMembers', () => {
  it('maps restored members from the api', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        {
          id: 'u1',
          full_name: 'sam rivera',
          phone_number: '+12025550101',
          restored_at: '2026-11-01T18:00:00Z',
          has_joined_whatsapp: false,
          recent_events: [],
        },
      ],
    });

    const { result } = renderHook(() => useRestoredMembers(), { wrapper: queryWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith('/api/auth/users/restored/');
    expect(result.current.data).toHaveLength(1);
    expect(result.current.data?.[0]).toMatchObject({
      id: 'u1',
      fullName: 'sam rivera',
      phoneNumber: '+12025550101',
      restoredAt: new Date('2026-11-01T18:00:00Z'),
      hasJoinedWhatsapp: false,
      recentEvents: [],
    });
  });
});
