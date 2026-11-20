import { renderHook, waitFor } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { type DevTestEventOptions, useCreateDevTestEvents } from './devTools';

vi.mock('@/api/client');

const OPTIONS: DevTestEventOptions = {
  isPast: false,
  isCanceled: false,
  isOfficial: false,
  isClub: false,
  eventFormat: 'restaurant',
  makeMeHost: false,
  makeMeGuest: false,
  price: '',
  venmoLink: '',
  cashappLink: '',
  zelleInfo: '',
  cohostCount: 0,
  invitedCohostCount: 0,
  goingCount: 0,
  maybeCount: 0,
  cantGoCount: 0,
  waitlistedCount: 0,
  invitedCount: 0,
  nonMemberGoingCount: 0,
  rsvpEnabled: true,
  visibility: 'public',
  maxAttendees: null,
  allowPlusOnes: false,
  requiredQuestionCount: 0,
  optionalQuestionCount: 0,
};

describe('useCreateDevTestEvents', () => {
  it.each([
    [true, 'restaurant'],
    [false, null],
  ])('sends event_format only for official events (official=%s)', async (isOfficial, expected) => {
    vi.mocked(apiClient.post).mockResolvedValue({ data: { id: '1', slug: 's' } });
    const { result } = renderHook(() => useCreateDevTestEvents(), { wrapper: queryWrapper() });

    result.current.mutate({ ...OPTIONS, isOfficial });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(apiClient.post).toHaveBeenLastCalledWith(
      '/api/community/dev/test-events/',
      expect.objectContaining({ event_format: expected }),
    );
  });
});
