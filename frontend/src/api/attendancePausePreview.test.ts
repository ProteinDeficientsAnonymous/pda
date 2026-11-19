import { describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';

import { fetchAttendancePausePreview, fetchGuidelinesPausePreview } from './attendancePausePreview';

vi.mock('@/api/client');

describe('fetchAttendancePausePreview', () => {
  it('fetches and maps the preview', async () => {
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
        stripped_roles: ['vetter'],
        clears_whatsapp: true,
      },
    });

    const preview = await fetchAttendancePausePreview('u1');

    expect(apiClient.get).toHaveBeenCalledWith('/api/auth/users/u1/attendance-pause-preview/');
    expect(preview.strippedRoles).toEqual(['vetter']);
    expect(preview.clearsWhatsapp).toBe(true);
    expect(preview.events).toEqual([
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
    vi.mocked(apiClient.get).mockResolvedValueOnce({
      data: { events: [], stripped_roles: [], clears_whatsapp: false },
    });

    expect(await fetchGuidelinesPausePreview('u1')).toEqual({
      events: [],
      strippedRoles: [],
      clearsWhatsapp: false,
    });
    expect(apiClient.get).toHaveBeenCalledWith('/api/auth/users/u1/guidelines-pause-preview/');
  });
});
