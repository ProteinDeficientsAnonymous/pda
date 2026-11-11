import { describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import { fetchAttendancePausePreview, fetchGuidelinesPausePreview } from './attendancePausePreview';

vi.mock('@/api/client');

describe('fetchAttendancePausePreview', () => {
  it('fetches and maps the affected events', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: {
        events: [
          {
            id: 'e1',
            title: 'Potluck',
            start_datetime: '2026-12-01T18:00:00Z',
            role: 'hosting',
            outcome: 'drafted',
          },
          { id: 'e2', title: 'Hike', start_datetime: null, role: 'rsvp', outcome: 'removed' },
        ],
      },
    });

    const events = await fetchAttendancePausePreview('u1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/auth/users/u1/attendance-pause-preview/');
    expect(events).toEqual([
      {
        id: 'e1',
        title: 'Potluck',
        startDatetime: new Date('2026-12-01T18:00:00Z'),
        role: 'hosting',
        outcome: 'drafted',
      },
      { id: 'e2', title: 'Hike', startDatetime: null, role: 'rsvp', outcome: 'removed' },
    ]);
  });

  it('fetches the guidelines pause preview', async () => {
    vi.mocked(apiClient.get).mockResolvedValueOnce({ data: { events: [] } });

    expect(await fetchGuidelinesPausePreview('u1')).toEqual([]);
    expect(apiClient.get).toHaveBeenCalledWith('/api/auth/users/u1/guidelines-pause-preview/');
  });
});
