import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { useOfficialEventDefaults } from './officialEventDefaults';

vi.mock('@/api/client');

const mockedGet = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useOfficialEventDefaults', () => {
  it('maps the wire defaults to camelCase', async () => {
    mockedGet.mockResolvedValueOnce({
      data: {
        cashapp_link: '$pdanyc',
        rsvp_questions: [
          { label: 'pronouns?', field_type: 'select', options: ['she', 'they'], required: true },
        ],
      },
    });

    const { result } = renderHook(() => useOfficialEventDefaults(true), {
      wrapper: queryWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));
    expect(mockedGet).toHaveBeenCalledWith('/api/community/official-event-defaults/');
    expect(result.current.data).toEqual({
      cashappLink: '$pdanyc',
      rsvpQuestions: [
        { label: 'pronouns?', fieldType: 'select', options: ['she', 'they'], required: true },
      ],
    });
  });

  it('does not fetch when disabled', () => {
    const { result } = renderHook(() => useOfficialEventDefaults(false), {
      wrapper: queryWrapper(),
    });

    expect(result.current.fetchStatus).toBe('idle');
    expect(mockedGet).not.toHaveBeenCalled();
  });
});
