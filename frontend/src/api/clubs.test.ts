import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { clubFromWire, useClubs } from './clubs';

vi.mock('@/api/client');

const mockedGet = vi.mocked(apiClient.get);

beforeEach(() => {
  vi.clearAllMocks();
});

describe('clubFromWire', () => {
  it('maps the wire shape to a club', () => {
    expect(clubFromWire({ id: 'c1', name: 'book club', requirements: 'read the book' })).toEqual({
      id: 'c1',
      name: 'book club',
      requirements: 'read the book',
    });
  });
});

describe('useClubs', () => {
  it('fetches and maps clubs', async () => {
    mockedGet.mockResolvedValueOnce({
      data: [
        { id: 'c1', name: 'book club', requirements: 'read the book' },
        { id: 'c2', name: 'run club', requirements: '' },
      ],
    });

    const { result } = renderHook(() => useClubs(), { wrapper: queryWrapper() });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(mockedGet).toHaveBeenCalledWith('/api/community/clubs/');
    expect(result.current.data).toEqual([
      { id: 'c1', name: 'book club', requirements: 'read the book' },
      { id: 'c2', name: 'run club', requirements: '' },
    ]);
  });
});
