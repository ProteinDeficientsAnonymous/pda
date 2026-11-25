import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { useJoinRequestSuggestedEvents } from './joinSuggestedEvents';

vi.mock('@/api/client');

describe('useJoinRequestSuggestedEvents', () => {
  it('maps the events and whether the club event is from a picked club', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        next_official_event: null,
        club_event: {
          id: 'c1',
          slug: 'movie-night',
          title: 'Movie Night',
          start_datetime: '2026-12-10T23:30:00Z',
        },
        club_event_from_picked_club: false,
      },
    });

    const { result } = renderHook(() => useJoinRequestSuggestedEvents('jr1'), {
      wrapper: queryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.get).toHaveBeenCalledWith(
      '/api/community/join-requests/jr1/suggested-events/',
    );
    expect(result.current.data).toEqual({
      nextOfficialEvent: null,
      clubEvent: {
        id: 'c1',
        slug: 'movie-night',
        title: 'Movie Night',
        startDatetime: new Date('2026-12-10T23:30:00Z'),
      },
      clubEventFromPickedClub: false,
    });
  });
});
