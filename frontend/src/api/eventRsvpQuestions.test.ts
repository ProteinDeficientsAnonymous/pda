import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EventRsvpQuestion } from '@/models/event';

import { apiClient } from './client';
import { syncEventRsvpQuestions } from './eventRsvpQuestions';

vi.mock('./client', () => ({
  apiClient: {
    put: vi.fn(),
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
    vi.mocked(apiClient.put).mockReset();
  });

  it('should replace all questions in one request', async () => {
    vi.mocked(apiClient.put).mockResolvedValue({
      data: [
        {
          id: 'keep',
          label: 'updated',
          field_type: 'textarea',
          options: [],
          required: false,
          display_order: 0,
        },
        {
          id: 'new',
          label: 'new',
          field_type: 'textarea',
          options: [],
          required: false,
          display_order: 1,
        },
      ],
    });

    const previous = [q({ id: 'keep', label: 'old' })];
    const result = await syncEventRsvpQuestions(
      'evt',
      [q({ id: 'keep', label: 'updated' }), q({ id: 'q-temp-new', label: 'new' })],
      previous,
    );

    expect(apiClient.put).toHaveBeenCalledWith('/api/community/events/evt/rsvp-questions/', {
      expected: [
        {
          id: 'keep',
          label: 'old',
          field_type: 'textarea',
          options: [],
          required: false,
        },
      ],
      questions: [
        {
          id: 'keep',
          label: 'updated',
          field_type: 'textarea',
          options: [],
          required: false,
        },
        {
          id: null,
          label: 'new',
          field_type: 'textarea',
          options: [],
          required: false,
        },
      ],
    });
    expect(result.map((question) => question.id)).toEqual(['keep', 'new']);
  });
});
