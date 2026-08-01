import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EventRsvpQuestion } from '@/models/event';

import { apiClient } from './client';
import { syncEventRsvpQuestions } from './eventRsvpQuestions';

vi.mock('./client', () => ({
  apiClient: {
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const q = (
  partial: Partial<EventRsvpQuestion> & Pick<EventRsvpQuestion, 'id'>,
): EventRsvpQuestion => ({
  label: 'q',
  fieldType: 'textarea',
  options: [],
  required: false,
  ...partial,
});

describe('syncEventRsvpQuestions', () => {
  beforeEach(() => {
    vi.mocked(apiClient.post).mockReset();
    vi.mocked(apiClient.patch).mockReset();
    vi.mocked(apiClient.delete).mockReset();
  });

  it('should create and update before deleting so a later failure keeps old questions', async () => {
    const order: string[] = [];
    vi.mocked(apiClient.post).mockImplementation(async () => {
      order.push('create');
      return {
        data: {
          id: 'new',
          label: 'new',
          field_type: 'textarea',
          options: [],
          required: false,
          display_order: 1,
        },
      };
    });
    vi.mocked(apiClient.patch).mockImplementation(async () => {
      order.push('update');
      return {
        data: {
          id: 'keep',
          label: 'updated',
          field_type: 'textarea',
          options: [],
          required: false,
          display_order: 0,
        },
      };
    });
    vi.mocked(apiClient.delete).mockImplementation(async () => {
      order.push('delete');
    });

    await syncEventRsvpQuestions(
      'evt',
      [q({ id: 'keep', label: 'updated' }), q({ id: 'temp-new', label: 'new' })],
      [q({ id: 'keep', label: 'old' }), q({ id: 'gone' })],
    );

    expect(order).toEqual(['update', 'create', 'delete']);
  });
});
