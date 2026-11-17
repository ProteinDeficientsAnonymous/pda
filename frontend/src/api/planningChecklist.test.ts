import { renderHook, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { apiClient } from '@/api/client';
import { queryWrapper } from '@/test/render';

import { useChecklist } from './planningChecklist';

vi.mock('@/api/client');

beforeEach(() => {
  vi.clearAllMocks();
});

describe('useChecklist', () => {
  it('loads the shared checklist', async () => {
    const items = [{ id: 'i1', text: 'secure venue', detail: '' }];
    vi.mocked(apiClient.get).mockResolvedValue({ data: items });
    const { result } = renderHook(useChecklist, { wrapper: queryWrapper() });
    await waitFor(() => {
      expect(result.current.data).toEqual(items);
    });
    expect(apiClient.get).toHaveBeenCalledWith('/api/community/planning/checklist/');
  });
});
